# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

GerdsenAI CLI is a terminal-based agentic coding assistant (Python 3.11+) that connects to **local** LLM servers (Ollama, LM Studio, vLLM, HuggingFace TGI) via OpenAI-compatible APIs, with optional Anthropic cloud support. Built on Typer + Rich + prompt_toolkit + httpx + Pydantic v2, fully async.

## Development Commands

**A `.venv` virtual environment is mandatory** — never install into system Python:

```bash
python3.11 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
python scripts/check_venv.py     # Verify venv is active and deps installed
```

### Testing
```bash
pytest                                                    # All tests (coverage gate: 40%)
pytest tests/test_modes.py -v                             # Single file
pytest tests/test_modes.py::TestExecutionMode::test_mode_values -v   # Single test
pytest -m "not integration"                               # Skip integration tests
pytest --cov=gerdsenai_cli --cov-report=html              # Coverage report
```
Coverage floor is `--cov-fail-under=40` in pyproject.toml — it reflects real current coverage, not an aspiration (raising it is tracked in docs/ROADMAP.md). pytest-asyncio runs in `asyncio_mode = "auto"` — async tests need no decorator.

### Linting & Type Checking
```bash
ruff check gerdsenai_cli/
ruff format gerdsenai_cli/
mypy gerdsenai_cli/          # Strict mode; non-blocking in CI but keep it clean
```

### Running
```bash
gerdsenai                        # Interactive TUI
python -m gerdsenai_cli          # Same, via module
gerdsenai -p "prompt"            # Headless one-shot (works config-free with GERDSENAI_LLM_SERVER_URL set)
gerdsenai --config examples/config/basic.json
```

CI (`.github/workflows/ci.yml`) runs ruff + mypy + pytest on Python 3.11/3.12/3.13, then builds with hatchling and verifies with twine. Note: hatchling is pinned `<1.28` in pyproject.toml because newer versions emit metadata twine rejects — don't unpin without checking.

## Architecture

### Request Flow

```
cli.py (Typer entry) → main.py GerdsenAICLI (startup, TUI loop)
  → SmartRouter (slash command vs. natural language intent)
    → CommandParser.execute_command()        # slash commands
    → Agent.process_user_input[_stream]()    # natural language
        → context building (ContextManager, memory, vector index, proactive context)
        → bounded tool loop:
            LLMClient.chat_with_tools() → providers/* → tool_parsing →
            ConfirmationEngine gate (mutating ops) → ToolRegistry.run() → repeat
        → streamed response to PromptToolkitTUI
```

Key orchestration classes:
- `GerdsenAICLI` (main.py) — startup sequence, TUI loop, command registration
- `Agent` (core/agent.py) — intent detection, context assembly, tool-loop orchestration
- `LLMClient` (core/llm_client.py) — provider routing, retries/backoff, native tool calling with fallback to `tool_shim.py` (prompt-based JSON tool calls for models without function calling)
- `tool_parsing.py` — normalizes model output across formats (Hermes XML, `<think>` reasoning blocks, OpenAI tool_calls)
- `ConfirmationEngine` (core/confirmation.py) — read-only tools run freely; mutating tools (file edit/create, terminal) require user approval unless in LLVL mode

### Provider Abstraction (core/providers/)

`LLMProvider` ABC in `base.py`; concrete providers: ollama, lm_studio, vllm, huggingface, anthropic (optional, via `[anthropic]` extra with keyring secrets), tailscale (discovers LLM servers on tailnet peers). `detector.py` auto-discovers servers on localhost ports and Tailscale. Everything degrades to a no-op when a backing service is unavailable.

### Command System (commands/)

Registry pattern, no decorators. To add a slash command:
1. Create a class extending `BaseCommand` (commands/base.py) — declare `name`, `aliases`, `category` (CommandCategory enum), argument definitions; implement `async execute(args) -> CommandResult`.
2. Instantiate and register it in `main.py`'s command initialization via `CommandParser.register_command()`.

Commands receive a shared context dict (llm_client, agent, settings, etc.). External skills (`.claude/skills/`, AGENTS.md via core/skill_loader.py) are also surfaced as commands.

### Configuration (config/)

- `settings.py` — Pydantic v2 Settings model (server URL, per-operation timeouts, context window, feature flags, agent profiles, user_preferences).
- `manager.py` — loads/saves `~/.config/gerdsenai-cli/config.json` (or `$GERDSENAI_CONFIG`).
- Precedence: **CLI flag > environment variable > config file**. Env vars: `GERDSENAI_LLM_SERVER_URL` (must be `http(s)://host:port` with explicit port — malformed values fail loudly), `GERDSENAI_MODEL`, `GERDSENAI_LLM_API_KEY`. Env values are never written back to the config file.

### Other Subsystems

- **Execution modes** (core/modes.py): CHAT (Q&A), ARCHITECT (plan-then-approve), EXECUTE (immediate), LLVL (no guards). Shift+Tab cycles modes in the TUI.
- **Vector index** (core/vector_store.py, repo_index.py, embeddings.py): Qdrant over REST (no client dep), Ollama embeddings first, sentence-transformers fallback via `[embeddings]` extra. Drives `/index`.
- **Memory** (core/memory.py): persistent cross-session topic/file tracking.
- **Planner / complexity / clarification / suggestions** (core/): Phase 8d intelligence systems.
- **Plugins** (plugins/): vision (LLaVA, Tesseract OCR) and audio (Whisper, Bark) — lazy-loaded, no-op when deps are missing.
- **Agent profiles** (core/agent_profiles.py): named personas binding system prompt + provider + model.

## Conventions

- **No emojis anywhere** — not in terminal output, not in the codebase. Use Rich markup (`[green]Success![/green]`) for visual feedback.
- Type hints required on all functions (mypy strict config in pyproject.toml).
- Async/await for all I/O; never block the TUI event loop.
- Optional dependencies (anthropic, keyring, sentence_transformers) must stay optional: guard imports and degrade gracefully; mypy overrides for them already exist in pyproject.toml.
- File mutations always go through FileEditor (diff preview + backup), never raw writes from agent paths.

## Key Docs

- `docs/development/CONTRIBUTING.md` — workflow and venv policy
- `docs/development/TESTING_GUIDE.md` — test patterns; manual TUI scenarios in `tests/manual/`
- `docs/ROADMAP.md` — planned capabilities, coverage targets, known type-error backlog
- `.github/copilot-instructions.md` — companion AI-agent instructions (keep consistent with this file)
- `examples/config/` — ready-to-use config files (basic, power-user, MCP)
