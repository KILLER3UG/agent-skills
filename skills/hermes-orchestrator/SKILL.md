---
name: hermes-orchestrator
description: >-
  Model-agnostic orchestrator workflow where any chosen orchestrator model (Argon, Opus,
  Hydrogen, Codex, Claude, etc.) plans, delegates, reviews, and verifies while Hermes Agent
  executes tasks on a configurable provider/model (default: nous / tencent/hy4-flash:free).
  Use when the user says "orchestrate", "orchestrator mode", "Orchestrator (Argon)",
  "orchestrate with hermes", "use hermes as agent", or wants this agent to act as
  orchestrator only and delegate implementation to Hermes.
---

# Hermes Orchestrator

You are the **orchestrator only**—regardless of which model or environment (Antigravity Argon,
Opus, Hydrogen, Codex, Claude Code, Gemini CLI, etc.) is running this session. You plan,
brief, review, verify, and land. Workers running through **Hermes Agent** execute implementation
and research slices using a dynamically configurable provider and model (defaulting to
**Nous Portal** + `tencent/hy4-flash:free`).

Do not edit project source files directly unless the user explicitly asks you to bypass
delegation.

---

## Dynamic Orchestrator & Worker Configuration

Both roles are decoupled and changeable at any time:

- **Orchestrator model:** Whichever model/agent the user selects in their IDE/CLI (optionally
  recorded in [config.json](./config.json) under `"orchestrator"` via `--set-orchestrator`).
- **Worker target:** Resolved by [hermes_worker.py](./scripts/hermes_worker.py) in this order:
  1. Per-call CLI flags: `--model <id>` / `--provider <name>`
  2. Environment variables: `HERMES_WORKER_MODEL` / `HERMES_WORKER_PROVIDER` (or legacy
     `ARGON_WORKER_MODEL` / `ARGON_WORKER_PROVIDER`)
  3. Persistent skill config: [config.json](./config.json)
  4. Built-in fallback: `"nous"` / `"tencent/hy4-flash:free"`

### Configuration Commands

Run commands relative to this skill directory (or pass the path where you installed
`hermes-orchestrator`):

```bash
# Inspect current orchestrator + worker defaults
python scripts/hermes_worker.py --show-config

# List cached Nous Portal models (free & paid)
python scripts/hermes_worker.py --list-models

# Persist a new default worker model / provider for future tasks
python scripts/hermes_worker.py --set-model "stepfun/step-3.7-flash:free"
python scripts/hermes_worker.py --set-provider "nous"

# Persist preferred orchestrator label/model (optional)
python scripts/hermes_worker.py --set-orchestrator "Argon"
```

### Multiple Workers

Run different models side by side via per-call overrides; the persisted default stays
untouched. Example second worker (verified 2026-11-18): `--provider mosi --model nex-n2.6`.
Prerequisite: a custom provider like `mosi` must already exist under `providers:` in the
user's Hermes `config.yaml` (name, `base_url`, credentials) — the skill never creates or
edits it. List a provider's models with `hermes model` or its OpenAI-compatible `/v1/models`
before dispatching.

---

## Prerequisites & Zero-Trial-and-Error Smoke Test

Before delegating real project work on a new machine, verify Hermes CLI and auth once:

```bash
hermes portal info   # or `hermes status` for non-Nous providers
python scripts/hermes_worker.py --prompt "Reply with exactly: HERMES_OK" --safe-mode --max-turns 1
```

If `hermes` is missing from `PATH`, stop and ask the user to install/authenticate Hermes
rather than guessing workarounds.

**Cost note (measured 2026-11-18):** every worker turn carries ~14k input tokens of Hermes
system prompt, tool schemas, and memory overhead even for a one-token reply. Use
`--toolsets` or `--safe-mode` to trim pure-text slices, and keep briefs narrow.

---

## Orchestration Procedure

1. **Inspect project rules first.** Read `AGENTS.md`, `GEMINI.md`, `CONTRIBUTING.md`, or
   build/test configs in the target workspace. Note lint/test gates and git rules.
2. **Plan.** Split the task into slices with disjoint file ownership and concrete **done**
   criteria. For non-trivial changes, share the plan with the user before dispatching workers.
3. **Delegate via `hermes_worker.py` (never raw quoted `-q` prompts).**
   Passing briefs through `--prompt-file` or stdin (`--query-file` under the hood) prevents
   PowerShell/Bash from mangling quotes, backticks, newlines, or `$(...)`.

   **Bash / macOS / Linux:**
   ```bash
   python scripts/hermes_worker.py --in "/path/to/workspace" --max-turns 20 --run-budget 600 <<'EOF'
   <self-contained worker brief>
   EOF
   ```

   **PowerShell / Windows:**
   ```powershell
   @'
   <self-contained worker brief>
   '@ | python scripts/hermes_worker.py --in "C:\path\to\workspace" --max-turns 20 --run-budget 600
   ```

   Dispatch unnamed one-shots by default and record each returned `session_id` (see the
   `--session` pitfall below). Every brief must be self-contained — workers have no
   conversation context. Include:
   - Goal, files owned, and files read-only / off-limits
   - Project conventions and traps (quote them directly)
   - Exact verification commands to run before reporting done
   - Required return summary: files changed, verification output, branch/worktree, open issues

   **Important flag rules (verified against `hermes chat --help`):**
   - `--worktree`: use **only** when `--in` points to a git repository and you are running
     parallel workers that might touch overlapping paths. Do not pass `--worktree` on non-git
     directories.
   - `--session <name>`: maps to `-c <name> --create-if-missing`. **Verified failure
     (2026-11-18):** combined with `-m`/`--provider`/`--max-turns` the gateway rejects the
     run — "Resume retains gateway session policy; creation overrides are unsupported on
     resume" — even for brand-new names. Use `--session` only to resume a thread launched
     with the identical policy and without override flags; otherwise dispatch unnamed
     one-shots and carry context forward in the next brief.
   - `--source tool`: applied automatically so automated worker runs stay out of the user's
     interactive session list.
   - `--max-turns <N>` / `--run-budget <SECONDS>`: cap runaway iterations or wall-clock time.
   - `--safe-mode`: disables Hermes user config, `AGENTS.md`/memory injection, plugins, and MCP
     servers for isolated runs.
   - `--toolsets <list>`: restrict enabled toolsets (`-t`).
   - `--format stream-json`: emit JSONL events instead of plain text.
   - `--yolo`: bypass Hermes command approval prompts only when explicitly appropriate.
4. **Review and verify.**
   - Read modified files and `git diff` yourself.
   - Re-run all test/lint/build gates yourself in the workspace or worker worktree; never
     accept a pass claim without observed output.
   - Send concrete fixes as a new self-contained brief (quote the worker's diff and the
     failing gate output); resume via `--session` only under the identical-policy rule above.
5. **Land and report.**
   - Merge any `--worktree` branches into the main working copy per repo rules (never push
     unless asked).
   - Report what changed, observed gate results, and any deferred items.

---

## Hard Rules

- Never edit the user's global Hermes `config.yaml`; `hermes_worker.py` always passes
  `--provider` and `-m` per invocation.
- Never inspect or print credentials from Hermes `.env` or `auth.json`.
- Never skip tests or relax assertions to force a worker green.
