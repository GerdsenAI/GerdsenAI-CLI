# GerdsenAI CLI - AI Agent Instructions
## Never use emojis in terminal output, or in the codebase at all
## Project Overview
GerdsenAI CLI is a terminal-based agentic coding assistant that connects to local LLM servers (Ollama, LocalAI) via OpenAI-compatible APIs. The agent can understand project context, edit files safely with diff previews, execute terminal commands with security controls, and maintain conversation state.

**Tech Stack**: Python 3.11+, async/await, Rich (terminal UI), httpx (HTTP client), Pydantic v2, pytest

## Architecture: Agentic Command System

### Core Components (4 pillars)
1. **Agent** (`core/agent.py`) - Intent parsing & orchestration. Analyzes LLM responses for action intents (edit, read, create, search files) using regex patterns and confidence scoring. Manages conversation context and pending edits.

2. **ContextManager** (`core/context_manager.py`) - Project analysis engine. Scans directories respecting `.gitignore`, categorizes files by MIME type, builds project trees, and provides focused context to the LLM.

3. **FileEditor** (`core/file_editor.py`) - Safe file operations with automatic backups, unified/side-by-side diffs, user confirmation prompts, and rollback capabilities. Never modifies files without preview.

4. **LLMClient** (`core/llm_client.py`) - Async HTTP client with streaming support, exponential backoff retry (2 retries default, configurable via `Settings.max_retries`), operation-specific timeouts, and health checking.

### Command System Pattern
Commands inherit from `BaseCommand` (`commands/base.py`) with:
- Declarative argument definitions (name, type, required, choices)
- Category-based organization (SYSTEM, MODEL, AGENT, FILE, CONTEXT)
- Automatic help generation and validation
- Async execution via `execute()` returning `CommandResult`

**Registration Flow**: `main.py` → `CommandParser` → `CommandRegistry` → command instances registered with name + aliases

Example command structure:
```python
class MyCommand(BaseCommand):
    @property
    def name(self) -> str: return "mycommand"
    
    @property
    def category(self) -> CommandCategory: return CommandCategory.SYSTEM
    
    def get_arguments(self) -> list[CommandArgument]: return [...]
    
    async def execute(self, args: list[str]) -> CommandResult: ...
```

## Critical Development Workflows

### Virtual Environment (MANDATORY)
**🚨 ALWAYS use the project virtual environment: `/Volumes/M2 Raid0/GerdsenAI_Repositories/GerdsenAI-CLI/.venv`**

```bash
# FIRST: Activate virtual environment (REQUIRED for ALL operations)
source .venv/bin/activate

# Verify you're in the venv
which python  # Should show: .venv/bin/python
python --version  # Should show: Python 3.11.x or 3.13.x

# If venv doesn't exist, create it:
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

**Why Virtual Environment is MANDATORY:**

1. **Consistent Python Version** - Everyone uses Python 3.11.13 (venv uses 3.11.13, supports 3.11-3.13)
2. **Dependency Isolation** - Project dependencies don't conflict with system packages
3. **No Module Errors** - All required packages are installed in venv
4. **Matches CI/CD** - Same environment as automated testing
5. **No System Pollution** - System Python remains clean

**Python Version Requirements:**
- Minimum: Python 3.11+
- Current venv: Python 3.11.13
- Supported: Python 3.11, 3.12, 3.13

**Before ANY command, verify venv:**
```bash
echo $VIRTUAL_ENV  # Should output: <project-path>/.venv
```

### Running & Testing (Inside .venv)
```bash
# Install editable mode (REQUIRED for module imports)
pip install -e ".[dev]"

# Run CLI (two methods)
python -m gerdsenai_cli
gerdsenai  # after install

# Run tests (must use pytest, not unittest)
pytest -v                    # all tests
pytest tests/test_*.py       # specific file
pytest -k "test_retry"       # pattern match

# Lint & format (use ruff, not black)
ruff check gerdsenai_cli/
ruff format gerdsenai_cli/

# Type check (strict mypy config)
mypy gerdsenai_cli/
```

**⚠️ If you see import errors:**
```bash
# 1. Check venv is active
echo $VIRTUAL_ENV

# 2. Reinstall in editable mode
pip install -e ".[dev]"

# 3. Verify installation
python -c "import gerdsenai_cli; print('✓ OK')"
```

### Configuration System
- Config stored: `~/.config/gerdsenai-cli/config.json`
- Model: `Settings` class (`config/settings.py`) with Pydantic v2 validators
- Access via `ConfigManager` (`config/manager.py`)
- **Important**: Uses `@field_validator` and `@model_validator` (Pydantic v2), NOT v1's `@validator`

### Terminal Safety Architecture
Terminal commands (`core/terminal.py`) have security layers:
- **Blocked commands**: `rm`, `format`, `shutdown`, etc. (always rejected in strict mode)
- **Allowed commands**: `ls`, `cat`, `grep` (no confirmation needed)
- **Requires confirmation**: Everything else (interactive prompt)
- Safety level configurable: "strict" (default), "moderate", "permissive"

## Project-Specific Conventions

### No Emojis Rule
**Never use emojis in terminal output** - this is a firm project rule. Use Rich formatting (colors, bold, panels) instead.

### Async Everywhere
All I/O operations MUST use async/await:
- File reads: `aiofiles` or `asyncio.to_thread()`
- HTTP: `httpx.AsyncClient`
- Terminal commands: `asyncio.create_subprocess_exec()`

### Rich Console Output Pattern
```python
from rich.console import Console
from ..utils.display import show_info, show_error, show_success

console = Console()
show_info("Processing...")  # Blue info message
show_success("Done!")        # Green success
show_error("Failed!")        # Red error with traceback
```

### Error Handling Standard
```python
try:
    result = await risky_operation()
except SpecificError as e:
    logger.error(f"Operation failed: {e}")
    show_error(f"User-friendly message: {e}")
    return CommandResult(success=False, message=str(e))
```

## Integration Points & Data Flow

### Agent Execution Flow
1. User input → `CommandParser.parse()` checks for slash commands
2. If not a command → `Agent.process_prompt()` 
3. LLM generates response → `IntentParser.parse_intent()` extracts actions
4. Action confidence > threshold → Execute (FileEditor, ContextManager, Terminal)
5. Conversation state updated → Display result

### LLM Communication Pattern
```python
# Streaming (default for chat)
async for chunk in llm_client.stream_chat(messages):
    console.print(chunk, end="")

# Non-streaming (for programmatic use)
response = await llm_client.send_chat_completion(messages)
content = response.choices[0]["message"]["content"]
```

### File Edit Safety Flow
1. `FileEditor.edit_file()` → read current content
2. Generate diff (unified or side-by-side)
3. Display diff with syntax highlighting
4. Prompt user for confirmation
5. Create backup → apply changes → update session
6. On error: automatic rollback from backup

## Testing Patterns

### Async Test Template
```python
@pytest.mark.asyncio
async def test_feature():
    # Arrange
    client = LLMClient(mock_settings)
    
    # Act  
    result = await client.method()
    
    # Assert
    assert result.success
    
    # Cleanup
    await client.close()
```

### Mocking HTTP Requests
Use `unittest.mock.patch` with `httpx.AsyncClient`:
```python
with patch.object(client.client, "get") as mock_get:
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"data": "value"}
    mock_get.return_value = mock_response
```

## Known Issues & Migration Needs

### Pydantic v2 Migration (IN PROGRESS)
Some files still use deprecated v1 syntax:
- ❌ `@validator` → ✅ `@field_validator`
- ❌ `@root_validator` → ✅ `@model_validator`
Check `TODO.md` for migration checklist.

### Command Naming Consolidation
Several command aliases exist for historical reasons (see `SLASH_COMMANDS.MD`). When modifying commands, prefer the primary name over aliases.

## Quick Reference: Key Files

- **Entry point**: `cli.py` (main function) → `main.py` (GerdsenAICLI class)
- **Command definitions**: `commands/{agent,files,model,system,terminal}.py`
- **Core logic**: `core/{agent,context_manager,file_editor,llm_client,terminal}.py`
- **UI utilities**: `utils/display.py` (Rich formatting helpers)
- **Config schema**: `config/settings.py` (Pydantic models)
- **Tests**: `tests/test_*.py` (pytest with asyncio plugin)

## Development Best Practices

1. **🚨 ALWAYS use .venv virtual environment** - `source .venv/bin/activate` before ANY command
2. **Verify venv before operations** - Check `echo $VIRTUAL_ENV` shows project path
3. **Install with `pip install -e ".[dev]"`** - module imports break otherwise
4. **Use ruff for linting/formatting** - configured in `pyproject.toml`
5. **Type hints required** - mypy strict mode enabled
6. **Test async code** - use `@pytest.mark.asyncio` decorator
7. **Respect gitignore** - ContextManager automatically filters files
8. **Preview before modify** - FileEditor always shows diffs
9. **Log errors** - use `logging` module + `show_error()` for user display
10. **Never use system Python** - System Python at `/opt/homebrew/bin/python3` is OFF LIMITS

## External Dependencies

- **Local LLM Server**: Default `http://localhost:11434` (Ollama)
- **OpenAI-compatible API**: `/v1/models`, `/v1/chat/completions` endpoints
- **Python 3.11+**: Required for modern type hints and `asyncio` features

## Commit Message Format
```
<type>: <description>

Types: feat, fix, chore, docs, refactor, test
Example: feat: add streaming chat completion support
```
