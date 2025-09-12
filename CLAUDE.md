# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Common Development Commands

### Running the Application
```bash
# Install in editable mode (required first)
pip install -e .

# Run the CLI
python -m gerdsenai_cli
# or
gerdsenai

# Run with debug mode
python -m gerdsenai_cli --debug
```

### Testing
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_llm_client.py
pytest tests/test_performance.py
pytest tests/test_terminal.py

# Run tests with verbose output
pytest -v
```

### Code Quality
```bash
# Lint and format (use ruff for everything)
ruff check gerdsenai_cli/
ruff format gerdsenai_cli/

# Type checking
mypy gerdsenai_cli/

# Legacy formatting (if needed)
black gerdsenai_cli/
```

### Development Setup
```bash
# Create virtual environment with Python 3.11+
python3.11 -m venv .venv --prompt "gerdsenai-cli"
source .venv/bin/activate

# Install in development mode
pip install -e .

# Verify installation
python -c "from gerdsenai_cli.commands.system import HelpCommand; print('✅ Import successful')"
```

## Architecture Overview

### Agent-Based Design
The application is built around an agentic architecture where an AI agent can:
- Understand project context through file scanning and gitignore parsing
- Edit files with diff previews and automatic backups
- Execute terminal commands with safety controls
- Maintain conversation state and context awareness

Key components:
- `Agent` (core/agent.py) - Main orchestration and intent parsing
- `ContextManager` (core/context_manager.py) - Project file analysis
- `FileEditor` (core/file_editor.py) - Safe file modifications
- `LLMClient` (core/llm_client.py) - Local LLM communication

### Command System
Commands use a plugin-like architecture with base classes:
- `BaseCommand` - Abstract base for all commands
- `CommandParser` - Routes user input to appropriate commands
- Command registration happens in `main.py` during initialization
- Commands are organized by category (agent, files, model, system, terminal)

### Configuration
- Config stored in `~/.config/gerdsenai-cli/config.json`
- Pydantic models for validation (currently using v1 validators - needs migration)
- First-run setup prompts for LLM server details
- Supports local LLM servers (Ollama default on localhost:11434)

## Important Development Notes

### Python Environment
- **Minimum**: Python 3.11+ (enforced in pyproject.toml)
- **Virtual Environment**: Always use `.venv` for development
- **Installation**: Must use `pip install -e .` for proper module loading

### Code Standards
- **No Emojis**: Never use emojis in UI (per clinerules.md)
- **Async/Await**: Use throughout for I/O operations
- **Type Hints**: Required for all functions
- **Rich Console**: Used for all terminal output

### Critical Issues to Address
- **Pydantic Migration**: Several files use deprecated v1 validators that need updating to v2
- **Command Consolidation**: TODO.md shows pending command renaming for consistency

### Commit Message Format
```
<type>: <description>

Types: feat, fix, chore, docs, refactor, test
Example: feat: add streaming chat completion support
```

## Key Integration Points

### LLM Integration
- OpenAI-compatible API format
- Async HTTP client (httpx) with connection pooling
- Streaming support for real-time responses
- Health checks and retry logic

### File Operations
- Respects `.gitignore` patterns
- Automatic backup creation before edits
- Unified and side-by-side diff previews
- Syntax-aware file filtering

### Terminal Safety
- Command validation before execution
- User confirmation for dangerous operations
- Command history logging
- Working directory awareness

## Testing Strategy
- Unit tests for core components
- Integration tests for LLM client
- Async test support with pytest-asyncio
- Mock external dependencies in tests

## Performance Targets
- Startup time: < 2 seconds
- Local operations: < 500ms
- Memory usage: < 100MB baseline
- Context building: < 2 seconds for typical projects
