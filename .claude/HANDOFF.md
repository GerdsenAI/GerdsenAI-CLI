# Handoff — first day on GerdsenAI CLI

Practical companion to `DREAM.md`. This is what I'd do first, in order, with the
exact files. Everything below is verified against the code on `main` as of this
handoff (post-PR #46).

## Orient yourself (15 minutes)

```bash
python3.11 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
gerdsenai --version            # smoke test
pytest -q                      # ~1150 tests, ~51% coverage, should be green
ruff check gerdsenai_cli/ && ruff format --check gerdsenai_cli/
```

Read, in this order:
1. `.claude/DREAM.md` (the why)
2. `CLAUDE.md` (repo conventions — match them)
3. `docs/ROADMAP.md` ("Agentic tool-use loop — in progress" + process notes)
4. `/root/.claude/plans/review-the-app-the-cheerful-hearth.md` — the **active
   ultraplan** (Phase 2b-3 and the file-referenced plan for everything after)

## The map of the agent loop (what you're building on)

| Piece | File | What it is |
|---|---|---|
| Loop engine | `core/tool_registry.py` | `run_agent_loop(client, messages, registry, confirm=, on_event=, max_iterations=)` → `LoopResult` |
| Tool set | `core/agent_tools.py` | `build_default_registry(agent)` → 7 tools (read/search/analyze/semantic + create/edit/run) |
| Dialect parsing | `core/tool_parsing.py` | `parse_model_output` (OpenAI/Hermes/shim/raw-text), `strip_reasoning` (`<think>`) |
| Tool-less shim | `core/tool_shim.py` | prompt-protocol fallback for models without native tools |
| Wire-in | `core/agent.py` | `_maybe_run_agent_loop`, `_tool_confirm` (~line 1675-1730); falls back to single-shot |
| Modes | `core/modes.py` | CHAT / ARCHITECT / EXECUTE / LLVL |
| Settings | `config/settings.py` | `enable_agent_loop` (True), `agent_loop_max_iterations` (10), `auto_confirm_edits`, `agent_mode` (pref) |

## Do these first (highest leverage, in order)

### 1. Mode sync — the #1 open gap (≈30 min) ⭐
**Symptom:** `core/agent.py` reads `agent_mode` from settings to gate autonomy,
but `main.py` reads `tui.get_mode()` only for UI routing (`main.py:1289`) and
**never writes it back to settings**. So the TUI's CHAT/ARCHITECT/EXECUTE/LLVL
selector doesn't actually drive the loop — it always runs as EXECUTE.

**Fix:** in `main.py`, before the agent processes a turn, sync the mode:
```python
self.agent.settings.set_preference("agent_mode", tui.get_mode().value)
```
Add a test asserting CHAT → no tools and EXECUTE → tools, end-to-end through
`main`'s handler. This unblocks everything else.

### 2. Live thinking + tool-event streaming — the soul (Phase 2b-3)
The loop already emits events; the UI just doesn't show them yet.
- Pass an `on_event` callback from `_maybe_run_agent_loop` into `run_agent_loop`
  (`core/tool_registry.py` fires `tool_call` / `tool_result` / `final`).
- Surface `ChatResult.reasoning` (already populated by `strip_reasoning`) dimmed
  + collapsible (a `/thinking` toggle already exists in the TUI).
- Render the tool events as distinct chunks. **Heads-up:** `system_info` is set
  but never rendered in `ui/prompt_toolkit_tui.py` (`get_formatted_text` ignores
  it) — fix or route around it; don't rely on it being visible.
- Confirm Escape cancels mid-chain (cancel infra already propagates) + add a test.

### 3. Headless `-p` (≈1 hr)
`cli.py:main()` only launches the TUI. Add `-p/--prompt` that runs one loop turn
and prints to stdout (and accept stdin). Unlocks scripting, CI, IDE use.

## Then (Phases 3–5, see the ultraplan)
- **Diff edits:** `apply_patch`/search-replace in `FileEditor` + a tool (reuse the
  existing preview/backup/confirm). Edits are full-file rewrites today.
- **MCP-as-tools:** `/mcp` (commands/mcp.py) is a stub — bridge MCP servers into
  `build_default_registry` so local models get the cloud tool ecosystem.
- **Model resilience:** tool-arg validation with a recoverable rejection message;
  `tool_choice` forcing where supported; a few-shot example in the tool prompt.
- **Foundation:** ~240 mypy errors (CI non-blocking), ~250 broad `except
  Exception`, 4 duplicated streaming loops in `main.py`, coverage gate 40% vs
  ~51% real.

## The working rhythm (please keep it — it's why this stayed clean)

- **One reviewable PR per change.** Branch from clean `main`, push, open PR.
- **Wait for CI green on 3.11/3.12/3.13**, then merge, then `git pull` main, then
  branch the next. Don't stack on an unmerged branch.
- **Gates with real exit codes** before every commit, at CI scope:
  ```bash
  ruff check gerdsenai_cli/; ruff format --check gerdsenai_cli/
  pytest -q                 # coverage must stay ≥ the gate
  python -m build && twine check dist/*
  ```
  (Pre-existing lint in `tests/` is outside CI's `gerdsenai_cli/` scope — don't
  chase it.) `mypy` is non-blocking, but **add no new errors** in files you touch.
- **Read the failing log, don't guess.** A past "flaky test" was really a
  `twine`/metadata-2.5 tooling break found only by reading the Actions job page;
  it's pinned via `hatchling<1.28` in `pyproject.toml` — revisit when twine
  accepts metadata 2.5.

## The non-negotiables (from DREAM.md, repeated because they matter)
- `run_command` **always** confirms except in LLVL. Never regress this.
- Every capability **degrades gracefully** when its backing service is absent.
- Keep the backup/undo/diff-preview on every mutating path.

Welcome aboard. Start with mode sync — it's small, it's satisfying, and it makes
the whole thing click. — Claude
