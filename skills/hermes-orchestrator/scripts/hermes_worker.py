"""Run or configure a Hermes Agent worker via `hermes chat --query-file`.

Worker provider/model resolution precedence (highest to lowest):
  1. CLI flags: --model / --provider
  2. Environment variables: HERMES_WORKER_MODEL / HERMES_WORKER_PROVIDER
     (also checks legacy aliases ARGON_WORKER_MODEL / ARGON_WORKER_PROVIDER)
  3. Skill config file: <skill_dir>/config.json
  4. Built-in defaults: provider="nous", model="tencent/hy4-flash:free"
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = SKILL_DIR / "config.json"

FALLBACK_ORCHESTRATOR = "auto"
FALLBACK_PROVIDER = "nous"
FALLBACK_MODEL = "tencent/hy4-flash:free"


def resolve_hermes_home() -> Path:
    """Resolve the local Hermes home directory across Windows, macOS, and Linux."""
    env_home = os.environ.get("HERMES_HOME")
    if env_home:
        return Path(env_home).expanduser()
    win_local = Path.home() / "AppData" / "Local" / "hermes"
    if win_local.exists():
        return win_local
    return Path.home() / ".hermes"


def load_skill_config(config_path: Path = CONFIG_PATH) -> dict[str, str]:
    """Load persisted orchestrator/worker defaults from config.json if present."""
    if not config_path.exists():
        return {
            "orchestrator": FALLBACK_ORCHESTRATOR,
            "provider": FALLBACK_PROVIDER,
            "model": FALLBACK_MODEL,
        }
    data = json.loads(config_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object in {config_path}")
    return {
        "orchestrator": str(data.get("orchestrator") or FALLBACK_ORCHESTRATOR),
        "provider": str(data.get("provider") or FALLBACK_PROVIDER),
        "model": str(data.get("model") or FALLBACK_MODEL),
    }


def save_skill_config(
    orchestrator: str,
    provider: str,
    model: str,
    config_path: Path = CONFIG_PATH,
) -> None:
    """Persist orchestrator label and worker provider/model to config.json."""
    config_path.write_text(
        json.dumps(
            {
                "orchestrator": orchestrator,
                "provider": provider,
                "model": model,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def resolve_worker_target(
    cli_provider: str | None,
    cli_model: str | None,
    config_path: Path = CONFIG_PATH,
) -> tuple[str, str]:
    """Resolve effective (provider, model) using CLI > env > config.json > fallback."""
    cfg = load_skill_config(config_path)
    provider = (
        cli_provider
        or os.environ.get("HERMES_WORKER_PROVIDER")
        or os.environ.get("ARGON_WORKER_PROVIDER")
        or cfg["provider"]
        or FALLBACK_PROVIDER
    )
    model = (
        cli_model
        or os.environ.get("HERMES_WORKER_MODEL")
        or os.environ.get("ARGON_WORKER_MODEL")
        or cfg["model"]
        or FALLBACK_MODEL
    )
    return provider, model


def print_nous_models(hermes_home: Path | None = None) -> int:
    """Print cached Nous Portal models from Hermes's local cache."""
    base = hermes_home or resolve_hermes_home()
    cache_path = base / "cache" / "nous_recommended_cache.json"
    if not cache_path.exists():
        print(
            f"Nous model cache not found at {cache_path}. "
            "Run `hermes portal` or `hermes model --refresh` first.",
            file=sys.stderr,
        )
        return 1
    raw = json.loads(cache_path.read_text(encoding="utf-8"))
    for portal_url, entry in raw.items():
        data = entry.get("data", {})
        print(f"Portal: {portal_url}")
        for section, label in (
            ("freeRecommendedModels", "Free models"),
            ("paidRecommendedModels", "Recommended models"),
        ):
            models = data.get(section) or []
            if not models:
                continue
            print(f"  {label}:")
            seen: set[str] = set()
            for item in models:
                name = item.get("modelName")
                if not name or name in seen:
                    continue
                seen.add(name)
                price = item.get("tokenPrice") or "n/a"
                print(f"    - {name} ({price})")
    return 0


def build_command(
    args: argparse.Namespace, query_file: str, provider: str, model: str
) -> list[str]:
    """Build the `hermes chat` argument list from parsed CLI options."""
    cmd = [
        "hermes",
        "chat",
        "--query-file",
        query_file,
        "--oneshot",
        "-Q",
        "--provider",
        provider,
        "-m",
        model,
        "--source",
        args.source,
        "--format",
        args.format,
    ]
    if args.accept_hooks:
        cmd.append("--accept-hooks")
    if args.in_dir:
        cmd.extend(["--in", args.in_dir])
    if args.session:
        cmd.extend(["-c", args.session, "--create-if-missing"])
    if args.worktree:
        cmd.append("--worktree")
    if args.max_turns is not None:
        cmd.extend(["--max-turns", str(args.max_turns)])
    if args.run_budget is not None:
        cmd.extend(["--run-budget", str(args.run_budget)])
    if args.toolsets:
        cmd.extend(["-t", args.toolsets])
    if args.reasoning:
        cmd.extend(["--reasoning", args.reasoning])
    if args.safe_mode:
        cmd.append("--safe-mode")
    if args.yolo:
        cmd.append("--yolo")
    return cmd


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments for the Hermes worker launcher."""
    parser = argparse.ArgumentParser(
        description="Invoke or configure a headless Hermes worker for any orchestrator."
    )
    prompt_group = parser.add_mutually_exclusive_group()
    prompt_group.add_argument(
        "--prompt-file",
        help="Path to UTF-8 prompt file (or '-' to read from stdin). Defaults to stdin when running a prompt.",
    )
    prompt_group.add_argument(
        "--prompt",
        help="Inline prompt text (written to a temp file before calling hermes).",
    )
    parser.add_argument("--in", dest="in_dir", help="Target workspace directory (--in).")
    parser.add_argument(
        "--session",
        help="Named session for multi-turn continuity (-c NAME --create-if-missing).",
    )
    parser.add_argument(
        "--worktree",
        action="store_true",
        help="Run in an isolated git worktree for parallel workers (git repos only).",
    )
    parser.add_argument(
        "--provider",
        help="Override provider for this run (default from HERMES_WORKER_PROVIDER or config.json).",
    )
    parser.add_argument(
        "-m",
        "--model",
        help="Override model for this run (default from HERMES_WORKER_MODEL or config.json).",
    )
    parser.add_argument(
        "--set-orchestrator",
        help="Persist preferred orchestrator model/label in config.json (e.g., Argon, Opus, Codex, auto).",
    )
    parser.add_argument("--set-model", help="Persist default worker model to config.json.")
    parser.add_argument(
        "--set-provider", help="Persist default worker provider to config.json."
    )
    parser.add_argument(
        "--show-config",
        action="store_true",
        help="Print effective orchestrator/worker configuration and exit.",
    )
    parser.add_argument(
        "--list-models",
        action="store_true",
        help="List cached Nous Portal models and exit.",
    )
    parser.add_argument("--source", default="tool")
    parser.add_argument("--format", choices=("text", "stream-json"), default="text")
    parser.add_argument("--max-turns", type=int)
    parser.add_argument("--run-budget", type=int)
    parser.add_argument("--toolsets", help="Comma-separated Hermes toolsets (-t).")
    parser.add_argument(
        "--reasoning",
        choices=("none", "minimal", "low", "medium", "high", "xhigh", "max", "ultra"),
    )
    parser.add_argument("--safe-mode", action="store_true")
    parser.add_argument("--yolo", action="store_true")
    parser.add_argument(
        "--no-accept-hooks",
        dest="accept_hooks",
        action="store_false",
        help="Do not pass --accept-hooks.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Handle config inspection/updates or execute a Hermes worker turn."""
    args = parse_args(argv)

    if args.set_model or args.set_provider or args.set_orchestrator:
        cfg = load_skill_config()
        new_orchestrator = args.set_orchestrator or cfg["orchestrator"]
        new_provider = args.set_provider or cfg["provider"]
        new_model = args.set_model or cfg["model"]
        save_skill_config(new_orchestrator, new_provider, new_model)
        print(
            json.dumps(
                {
                    "config_path": str(CONFIG_PATH),
                    "orchestrator": new_orchestrator,
                    "provider": new_provider,
                    "model": new_model,
                },
                indent=2,
            )
        )
        if not args.prompt_file and args.prompt is None:
            return 0

    if args.show_config:
        cfg = load_skill_config()
        eff_provider, eff_model = resolve_worker_target(args.provider, args.model)
        print(
            json.dumps(
                {
                    "config_path": str(CONFIG_PATH),
                    "persisted": cfg,
                    "effective": {
                        "orchestrator": cfg["orchestrator"],
                        "provider": eff_provider,
                        "model": eff_model,
                    },
                },
                indent=2,
            )
        )
        return 0

    if args.list_models:
        return print_nous_models()

    if shutil.which("hermes") is None:
        print(
            "Error: `hermes` CLI not found on PATH. Install Hermes Agent and authenticate "
            "(e.g. `hermes portal`) before delegating work.",
            file=sys.stderr,
        )
        return 127

    provider, model = resolve_worker_target(args.provider, args.model)
    temp_path: str | None = None
    try:
        if args.prompt_file and args.prompt_file != "-":
            query_file = os.path.abspath(args.prompt_file)
        else:
            prompt_text = args.prompt if args.prompt is not None else sys.stdin.read()
            if not prompt_text.strip():
                print("Error: prompt is empty.", file=sys.stderr)
                return 2
            fd, temp_path = tempfile.mkstemp(prefix="hermes_worker_", suffix=".md")
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(prompt_text)
            query_file = temp_path

        cmd = build_command(args, query_file, provider, model)
        proc = subprocess.run(cmd, cwd=args.in_dir or None, check=False)
        return proc.returncode
    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)


if __name__ == "__main__":
    raise SystemExit(main())
