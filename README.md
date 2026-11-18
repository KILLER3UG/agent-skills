# agent-skills

Cross-agent skills and runner utilities designed for **Antigravity**, **Codex**, **Claude Code**, **Gemini CLI**, and **Hermes Agent**.

Each skill is self-contained, cross-platform, and documented with exact commands, flag references, and offline tests so other agents can adopt and run them without trial and error.

---

## Included Skills

| Skill | Purpose | Default Backend | Location |
|---|---|---|---|
| `hermes-orchestrator` | Model-agnostic orchestrator workflow where your chosen orchestrator model plans, delegates, reviews, and verifies while Hermes Agent executes tasks. | `nous` / `tencent/hy4-flash:free` (configurable anytime) | [SKILL.md](./skills/hermes-orchestrator/SKILL.md) |

---

## Quick Install

Copy (or symlink) the desired skill folder from `skills/<skill-name>` into your agent's global or project skills directory:

| Agent / Environment | Global Skills Path | Project Skills Path |
|---|---|---|
| **Antigravity** | `~/.gemini/config/skills/` | `.agents/skills/` (or `.agents/skills.json`, already configured here) |
| **Codex** | `~/.codex/skills/` | `.agents/skills/` |
| **Claude Code** | `~/.claude/skills/` | `.claude/skills/` |
| **Hermes Agent** | `~/.hermes/skills/` (Windows: `%LOCALAPPDATA%\hermes\skills\`) | `.hermes/skills/` |

### Example (Windows PowerShell — install `hermes-orchestrator` globally for Antigravity)

```powershell
Copy-Item -Recurse -Force ".\skills\hermes-orchestrator" "$HOME\.gemini\config\skills\hermes-orchestrator"
```

### Example (macOS / Linux — install `hermes-orchestrator` globally)

```bash
mkdir -p ~/.gemini/config/skills
cp -R ./skills/hermes-orchestrator ~/.gemini/config/skills/hermes-orchestrator
```

---

## Using `hermes-orchestrator`

1. **Choose any orchestrator model** in your IDE/CLI (e.g., Argon, Opus, Hydrogen, Codex, Claude, GPT). The orchestrator plans, splits work, reviews diffs, and runs verification gates.
2. **Choose any Hermes worker model/provider** dynamically without editing skill code:

   ```bash
   # Show current orchestrator & worker configuration
   python skills/hermes-orchestrator/scripts/hermes_worker.py --show-config

   # List cached Nous Portal models (free & paid)
   python skills/hermes-orchestrator/scripts/hermes_worker.py --list-models

   # Persist a new default worker model or provider
   python skills/hermes-orchestrator/scripts/hermes_worker.py --set-model "stepfun/step-3.7-flash:free"
   python skills/hermes-orchestrator/scripts/hermes_worker.py --set-provider "nous"

   # Record which orchestrator model/persona you prefer (optional metadata)
   python skills/hermes-orchestrator/scripts/hermes_worker.py --set-orchestrator "Argon"
   ```

3. **Run a smoke test** (requires `hermes` CLI installed and authenticated, e.g. `hermes portal`):

   ```bash
   python skills/hermes-orchestrator/scripts/hermes_worker.py --prompt "Reply with exactly: HERMES_OK" --safe-mode --max-turns 1
   ```

See [SKILL.md](./skills/hermes-orchestrator/SKILL.md) for the full orchestration workflow, parallel `--worktree` isolation, and multi-turn `--session` usage.

---

## Verification & Testing

Run the offline unit test suite (requires Python 3.10+, no network calls):

```bash
python -m unittest discover -s tests -v
```
