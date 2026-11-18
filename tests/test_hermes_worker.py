"""Offline unit tests for skills/hermes-orchestrator/scripts/hermes_worker.py."""

from __future__ import annotations

import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

SCRIPT_DIR = (
    Path(__file__).resolve().parent.parent
    / "skills"
    / "hermes-orchestrator"
    / "scripts"
)
sys.path.insert(0, str(SCRIPT_DIR))

import hermes_worker  # noqa: E402


class HermesWorkerTests(unittest.TestCase):
    def test_load_and_save_config_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cfg_path = Path(tmp) / "config.json"
            default_cfg = hermes_worker.load_skill_config(cfg_path)
            self.assertEqual(default_cfg["orchestrator"], "auto")
            self.assertEqual(default_cfg["provider"], "nous")
            self.assertEqual(default_cfg["model"], "tencent/hy4-flash:free")

            hermes_worker.save_skill_config(
                "Argon", "openrouter", "stepfun/step-3.7-flash:free", cfg_path
            )
            loaded = hermes_worker.load_skill_config(cfg_path)
            self.assertEqual(loaded["orchestrator"], "Argon")
            self.assertEqual(loaded["provider"], "openrouter")
            self.assertEqual(loaded["model"], "stepfun/step-3.7-flash:free")

    def test_resolution_precedence_cli_env_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cfg_path = Path(tmp) / "config.json"
            hermes_worker.save_skill_config(
                "Opus", "nous", "tencent/hy4-flash:free", cfg_path
            )

            with mock.patch.dict(os.environ, {}, clear=True):
                self.assertEqual(
                    hermes_worker.resolve_worker_target(None, None, cfg_path),
                    ("nous", "tencent/hy4-flash:free"),
                )

            with mock.patch.dict(
                os.environ,
                {
                    "HERMES_WORKER_PROVIDER": "kilocode",
                    "HERMES_WORKER_MODEL": "upstage/solar-mini4:free",
                },
                clear=True,
            ):
                self.assertEqual(
                    hermes_worker.resolve_worker_target(None, None, cfg_path),
                    ("kilocode", "upstage/solar-mini4:free"),
                )
                self.assertEqual(
                    hermes_worker.resolve_worker_target(
                        "nous", "stepfun/step-3.7-flash:free", cfg_path
                    ),
                    ("nous", "stepfun/step-3.7-flash:free"),
                )

    def test_build_command_flags(self) -> None:
        args = hermes_worker.parse_args(
            [
                "--in",
                "/repo",
                "--session",
                "w1",
                "--worktree",
                "--max-turns",
                "5",
                "--run-budget",
                "120",
                "--toolsets",
                "file,terminal",
                "--reasoning",
                "medium",
                "--safe-mode",
                "--yolo",
                "--format",
                "stream-json",
            ]
        )
        cmd = hermes_worker.build_command(
            args, "/tmp/prompt.md", "nous", "tencent/hy4-flash:free"
        )
        self.assertEqual(cmd[:7], ["hermes", "chat", "--query-file", "/tmp/prompt.md", "--oneshot", "-Q", "--provider"])
        self.assertIn("nous", cmd)
        self.assertIn("tencent/hy4-flash:free", cmd)
        self.assertIn("--accept-hooks", cmd)
        self.assertIn("--worktree", cmd)
        self.assertIn("--safe-mode", cmd)
        self.assertIn("--yolo", cmd)
        self.assertIn("--create-if-missing", cmd)
        self.assertEqual(cmd[cmd.index("--format") + 1], "stream-json")

    def test_print_nous_models_from_cache(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cache_dir = Path(tmp) / "cache"
            cache_dir.mkdir(parents=True)
            cache_file = cache_dir / "nous_recommended_cache.json"
            cache_file.write_text(
                json.dumps(
                    {
                        "https://portal.nousresearch.com": {
                            "data": {
                                "freeRecommendedModels": [
                                    {
                                        "modelName": "tencent/hy4-flash:free",
                                        "tokenPrice": "$0.00/1M",
                                    }
                                ],
                                "paidRecommendedModels": [
                                    {
                                        "modelName": "x-ai/grok-4.7",
                                        "tokenPrice": "in $2.00 / out $6.00 per 1M",
                                    }
                                ],
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = hermes_worker.print_nous_models(Path(tmp))
            self.assertEqual(rc, 0)
            out = buf.getvalue()
            self.assertIn("tencent/hy4-flash:free", out)
            self.assertIn("x-ai/grok-4.7", out)

    def test_resolve_hermes_home_prefers_env(self) -> None:
        with mock.patch.dict(os.environ, {"HERMES_HOME": "/custom/hermes"}, clear=True):
            self.assertEqual(hermes_worker.resolve_hermes_home(), Path("/custom/hermes"))


if __name__ == "__main__":
    unittest.main()
