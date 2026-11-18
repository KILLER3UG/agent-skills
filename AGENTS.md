# Agent Guidelines (`agent-skills`)

This repository is a cross-agent skill collection (Antigravity, Codex, Claude Code, Gemini CLI, Hermes Agent, and compatible tools). Follow these rules so any agent can discover, install, run, and extend skills without trial and error.

## Repository Layout

- `skills/<skill-name>/SKILL.md` — Primary skill instructions with required YAML frontmatter (`name`, `description`).
- `skills/<skill-name>/config.json` — Optional runtime defaults (must remain free of secrets or machine-specific user paths).
- `skills/<skill-name>/scripts/` — Cross-platform helper scripts using Python standard library when possible.
- `skills/<skill-name>/references/` — Optional deep reference docs loaded only on demand.
- `.agents/skills.json` — Registers `skills` for Antigravity workspace auto-discovery.
- `tests/` — Offline unit tests validating helper scripts without live API/network calls.

## Rules for Contributors and Agents

1. **Keep skills portable:**
   - Never hardcode OS user home paths (for example `C:\Users\<name>\...` or `/home/<name>/...`). Resolve skill paths relative to `SKILL.md` / `__file__` and tool homes via environment variables (`HERMES_HOME`) or `Path.home()`.
   - Never commit API keys, OAuth tokens, `.env` files, or `auth.json`.
2. **Document exact commands and flags:**
   - Only document CLI flags and exit behaviors that are verified against the installed tool.
   - Include a non-destructive smoke-test command in every skill that invokes an external CLI.
3. **Verify before pushing:**
   - Run `python -m unittest discover -s tests -v` and confirm all tests pass after edits.
   - Confirm `git status` and `git diff` contain no temporary artifacts or secrets.
