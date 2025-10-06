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
- Track intelligence activities with real-time progress updates
- Plan multi-step operations and manage memory across sessions

Key components:
- `Agent` (core/agent.py) - Main orchestration and LLM-based intent parsing
- `ContextManager` (core/context_manager.py) - Project file analysis with dynamic context building
- `FileEditor` (core/file_editor.py) - Safe file modifications with automatic backups
- `LLMClient` (core/llm_client.py) - Local LLM communication with streaming and context window detection
- `TaskPlanner` (core/planner.py) - Multi-step task planning and execution tracking
- `ProjectMemory` (core/memory.py) - Persistent project knowledge across sessions
- `ProactiveSuggestor` (core/suggestions.py) - Context-aware code improvement suggestions

### Command System
Commands use a plugin-like architecture with base classes:
- `BaseCommand` - Abstract base for all commands
- `CommandParser` - Routes user input to appropriate commands
- Command registration happens in `main.py` during initialization
- Commands are organized by category (agent, files, model, system, terminal, intelligence)
- LLM-based intent detection for natural language input (no slash commands required)

### Configuration
- Config stored in `~/.config/gerdsenai-cli/config.json`
- Pydantic v2 models for validation (migration complete)
- First-run setup prompts for LLM server details
- Supports local LLM servers (Ollama default on localhost:11434)
- Auto-detects context window size (4K to 1M+ tokens) with configurable usage ratio
- Settings include: model_context_window, context_window_usage, auto_read_strategy

## Important Development Notes

### Python Environment
- **Minimum**: Python 3.11+ (enforced in pyproject.toml)
- **Virtual Environment**: Always use `.venv` for development
- **Installation**: Must use `pip install -e .` for proper module loading

### Code Standards
- **No Emojis**: Never use emojis in UI (strict project rule)
- **Async/Await**: Use throughout for I/O operations
- **Type Hints**: Required for all functions (mypy strict mode)
- **Rich Console**: Used for all terminal output
- **prompt_toolkit**: Used for TUI implementation (3-panel layout)

### UI Architecture
- **EnhancedConsole** (ui/console.py) - Rich-based console with status display integration
- **StatusDisplayManager** (ui/status_display.py) - Intelligence activity tracking (12 activity types)
- **prompt_toolkit TUI** (ui/prompt_toolkit_tui.py) - Full-featured TUI with embedded input
- **Intelligence Activities**: IDLE, THINKING, READING_FILES, WRITING_CODE, DETECTING_INTENT, ANALYZING_CONTEXT, RECALLING_MEMORY, PLANNING, EXECUTING_PLAN, GENERATING_SUGGESTIONS, ASKING_CLARIFICATION, CONFIRMING_OPERATION

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
- Streaming support for real-time responses (token-by-token)
- Health checks and retry logic with exponential backoff
- Context window auto-detection (15+ model families: GPT-4 128K, Gemini Pro 1M, Llama 3 8K, etc.)
- LLM-based intent detection (fast inference, temperature=0.3, max_tokens=300)
- JSON response format for action intents with confidence scoring

### File Operations
- Respects `.gitignore` patterns
- Automatic backup creation before edits with rollback capabilities
- Unified and side-by-side diff previews with syntax highlighting
- Syntax-aware file filtering
- Dynamic context building with 7-tier file prioritization (mentioned → recent → core → rest)
- Token budget management and intelligent file summarization
- Strategies: "smart" (prioritized), "whole_repo" (chunked), "iterative" (LLM-guided)

### Terminal Safety
- Command validation before execution
- User confirmation for dangerous operations
- Command history logging
- Working directory awareness

## Testing Strategy
- Unit tests for core components (pytest with asyncio support)
- Integration tests for LLM client and agent logic
- Phase-specific test suites (test_phase8c_context.py, test_intelligence_tracking.py)
- Visual test documentation (PHASE_*_RESULTS.md)
- Mock external dependencies in tests using unittest.mock
- Test reports with detailed metrics (PHASE_8B_TEST_REPORT.md)

## Performance Targets
- Startup time: < 2 seconds
- Local operations: < 500ms
- Memory usage: < 100MB baseline
- Context building: < 2 seconds for typical projects
- Intent detection: ~2s average (local LLM)
- Streaming response: First token < 2s

## Recent Feature Additions (Phase 8c-8d)

### Intelligence Activity Tracking
- Real-time status display with 12 activity types
- Progress tracking (0.0-1.0) with step information
- Activity history and statistics
- `/intelligence` command: status, history, stats, clear subcommands
- Integration throughout agent lifecycle (intent detection, context building, planning, execution)

### TUI Enhancement
- prompt_toolkit-based Application with 3-panel layout
- Embedded input (no display interruption)
- Real-time streaming with FormattedText rendering
- Scrollable conversation history with timestamps
- Native keyboard handling and auto-scroll

### Context Window Management (Phase 8c)
- Auto-detection for 15+ model families
- Dynamic context building with token budget management
- 80% context usage default (20% reserved for response)
- File summarization with beginning + end strategy
- Three strategies: smart, whole_repo, iterative

## Key Commands & Workflows

### Essential Commands
- `/help` - Show all available commands
- `/tools` - List tools by category with search/filter
- `/status` - System and AI connection status
- `/intelligence [status|history|stats|clear]` - Intelligence activity tracking
- `/agent` - Agent statistics and context information
- `/models` - List available models
- `/model <name>` - Switch to specific model

### File Operations
- `/ls [path]` - List files in project directory
- `/cat <file>` - Read and display file contents
- `/edit <file> "description"` - AI-assisted file editing
- `/create <file> "description"` - Create new files
- `/search <pattern>` - Search across project files

### Natural Language Interaction
User can type naturally without slash commands:
- "explain agent.py" → Auto-detects read_file intent
- "analyze this project" → Auto-detects analyze_project intent
- "where is error handling" → Auto-detects search_files intent
- Intent detection uses LLM with 95%+ confidence threshold
- Slash commands still work for power users (backward compatible)
