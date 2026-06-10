# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

GerdsenAI CLI is a terminal-based agentic coding assistant (Python 3.11+) that connects to local LLM servers (Ollama by default, plus vLLM, LM Studio, HuggingFace TGI) via OpenAI-compatible APIs, with optional cloud support (Anthropic via keyring). It provides project context awareness, safe file editing with diff previews, gated terminal command execution, and a real tool-calling agent loop.

## Development Commands

### Environment Setup (MANDATORY)
Always work inside the project virtual environment. Never use system Python.

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"          # editable install required, or module imports break
echo $VIRTUAL_ENV                # verify before any command
```

### Running
```bash
gerdsenai                        # interactive TUI (after install)
python -m gerdsenai_cli          # equivalent module invocation
gerdsenai -p "prompt"            # headless one-shot mode (also --stdin)
```

### Testing
```bash
pytest                           # all tests (asyncio_mode=auto; coverage gate: 40%)
pytest tests/test_llm_client.py  # single file
pytest -k "test_retry"           # pattern match
pytest -m "not integration"      # exclude integration tests
pytest --cov=gerdsenai_cli       # coverage report (HTML output in htmlcov/)
```

Custom pytest options for live-LLM tests: `--llm-provider`, `--llm-host`, `--llm-port`, `--llm-model` (defaults to Ollama on localhost:11434). An autouse fixture mocks tiktoken downloads so tests run offline.

### Lint / Format / Type Check
```bash
ruff check gerdsenai_cli/        # lint (use ruff, not black/flake8)
ruff format gerdsenai_cli/      # format in-place — CI has a format gate
mypy gerdsenai_cli/              # strict mode (non-blocking in CI)
```

Ruff: line length 88, target py311, rules E/W/F/I/B/C4/UP (E501/B008 ignored). CI runs the matrix on Python 3.11/3.12/3.13.

### Build
```bash
python -m build                  # wheel + sdist into dist/ (hatchling, pinned <1.28)
twine check dist/*
```

## Architecture

### Entry Point Flow
`cli.py` (Typer app, entry point `gerdsenai`) → `main.py` `GerdsenAICLI` class → wires `ConfigManager` → `Settings` → `LLMClient` → `Agent` → `CommandParser` → `PromptToolkitTUI` → interactive loop. Headless mode (`-p`/`--stdin`) routes through `run_headless()` for single-turn async execution.

Per user input: slash commands go to `CommandParser.parse()`; everything else goes to `Agent.process_prompt()`, which may run the agent loop.

### Core Pillars (`gerdsenai_cli/core/`)
- **Agent** (`agent.py`) — orchestration, intent parsing (`IntentParser`, `ActionIntent`, confidence scoring), conversation context, agent-loop wiring (`_maybe_run_agent_loop()`, `_tool_confirm()`).
- **LLMClient** (`llm_client.py`) — async httpx client for OpenAI-compatible endpoints; streaming, exponential backoff retry (2 retries default), operation-specific timeouts (health 10s, models 30s, chat/stream 600s).
- **ContextManager** (`context_manager.py`) — project scanning respecting `.gitignore`, MIME-type categorization, file trees, token-aware summarization.
- **FileEditor** (`file_editor.py`) — backups before modification, unified/side-by-side diffs with syntax highlighting, confirmation prompts, rollback on error. Never modifies files without preview.
- **Terminal** (`terminal.py`) — command execution with safety layers: blocked commands (`rm`, `format`, `shutdown` — always rejected in strict mode), allowed read-only commands (no confirmation), everything else requires confirmation. Safety level: "strict" (default) / "moderate" / "permissive".

### Agent Loop & Tools
- `core/agent_tools.py` builds the default tool registry: read-only tools (`read_file`, `search_files`, `analyze_project`, `semantic_search`) and gated mutating tools (`create_file`, `edit_file`, `run_command`).
- `core/tool_registry.py` runs the iteration loop (`run_agent_loop()`, max 10 iterations default).
- `core/tool_parsing.py` parses multiple tool-call dialects (OpenAI JSON, Hermes XML, shim JSON, raw-text recovery) and strips `<think>` reasoning blocks.
- `core/tool_shim.py` provides a prompt-based fallback protocol for models without native tool support.
- Four autonomy modes: CHAT (no tools), ARCHITECT (confirm mutations), EXECUTE (auto-edit), LLVL (trust all).

### Command System (`gerdsenai_cli/commands/`)
Commands inherit from `BaseCommand` (`commands/base.py`) with declarative arguments, category enum (SYSTEM, MODEL, AGENT, FILE, CONTEXT), auto-generated help, and async `execute()` returning `CommandResult`. Registration flow: `main.py` → `CommandParser` → registry with names + aliases. Prefer primary command names over historical aliases when modifying commands.

### Providers (`core/providers/`)
`detector.py` auto-discovers local servers (Ollama, vLLM, LM Studio, HuggingFace TGI) across localhost and Tailscale; `anthropic.py` is the cloud provider using keyring for secrets. All implement `BaseProvider`.

### Configuration (`gerdsenai_cli/config/`)
- `Settings` (`settings.py`) — Pydantic v2 model (use `@field_validator`/`@model_validator`, NOT v1 `@validator`).
- `ConfigManager` (`manager.py`) — loads `~/.config/gerdsenai-cli/config.json` with env overrides: `GERDSENAI_CONFIG`, `GERDSENAI_LLM_SERVER_URL`, `GERDSENAI_MODEL`, `GERDSENAI_LLM_API_KEY`.

### Other Subsystems
- **TUI** (`ui/prompt_toolkit_tui.py`) — interactive prompt_toolkit UI with history, mode selection, live streaming of the agent loop (thinking + tool events).
- **Phase 8d intelligence** (`core/`): `clarification.py` (ambiguity detection), `complexity.py` (task risk scoring), `confirmation.py` (snapshots + undo), `suggestions.py` (proactive suggestions).
- **Plugins** (`plugins/`) — registry-based loader with audio (transcribe/speak) and vision (image/OCR) plugins.
- **Supporting**: `token_counter.py` (tiktoken), `rate_limiter.py` (token bucket), `cache.py` (TTL response cache), `repo_index.py`/`vector_store.py`/`embeddings.py` (Qdrant semantic search — the Qdrant client is pooled; close it properly), `constants.py` (centralized magic numbers).

## Project-Specific Conventions

- **No emojis** — never in terminal output or anywhere in the codebase. Use Rich formatting (colors, bold, panels) instead.
- **Async everywhere** — all I/O uses async/await: `httpx.AsyncClient`, `asyncio.to_thread()` for files, `asyncio.create_subprocess_exec()` for commands.
- **Rich console output** — use `utils/display.py` helpers (`show_info`, `show_error`, `show_success`, `show_warning`), not bare `print()`.
- **Error handling** — catch specific exceptions, log via `logging`, display via `show_error()`, return `CommandResult(success=False, ...)` from commands.
- **Type hints required** — mypy strict mode (optional deps anthropic/keyring/sentence_transformers are excluded).
- **Commit messages** — `<type>: <description>` with types: feat, fix, chore, docs, refactor, test.

## Key Documentation

- `docs/TODO.md` and `docs/ROADMAP.md` — task tracking and planned capabilities
- `docs/development/` — CONTRIBUTING.md, TESTING_GUIDE.md, slash command docs
- `.claude/HANDOFF.md` — concrete onboarding checklist; `.claude/DREAM.md` — vision statement
- `CHANGELOG.md` / `UPGRADE_GUIDE.md` — change history and migration notes
- `.github/copilot-instructions.md` — companion AI-agent guide (kept in sync with this file)
