# TODO: GerdsenAI CLI Development Plan

This document outlines the development plan for the GerdsenAI CLI, a terminal-based agentic coding tool that connects to local AI models.

## Phase 1: Project Scaffolding & Core Setup

### Task 1: Initialize Python Project
- [ ] Create `pyproject.toml` with modern Python packaging
  - [ ] Set minimum Python version to 3.11+
  - [ ] Use `poetry` or `pip` with `pyproject.toml` format
  - [ ] Define project metadata (name: "gerdsenai-cli", version: "0.1.0")
  - [ ] Add description: "A terminal-based agentic coding tool for local AI models"
- [ ] Add core dependencies (latest stable versions):
  - [ ] `typer>=0.9.0` - Modern CLI framework (replacement for Click)
  - [ ] `rich>=13.0.0` - Beautiful terminal output and formatting
  - [ ] `httpx>=0.25.0` - Modern async HTTP client
  - [ ] `python-dotenv>=1.0.0` - Environment variable management
  - [ ] `pydantic>=2.4.0` - Data validation and settings management
  - [ ] `colorama>=0.4.6` - Cross-platform colored terminal text

### Task 2: Create Project Structure
- [ ] Create main application directory: `gerdsenai_cli/`
- [ ] Create `gerdsenai_cli/__init__.py` with version info
- [ ] Create `gerdsenai_cli/main.py` as the CLI entry point
- [ ] Create subdirectories:
  - [ ] `gerdsenai_cli/config/` - Configuration management
  - [ ] `gerdsenai_cli/core/` - Business logic (LLM client, context manager)
  - [ ] `gerdsenai_cli/commands/` - Slash command implementations
  - [ ] `gerdsenai_cli/utils/` - Utility functions
- [ ] Create entry point script: `gerdsenai_cli/cli.py`

### Task 3: Implement Startup Screen
- [ ] Create `gerdsenai_cli/utils/display.py`
- [ ] Implement function to read ASCII art from `gerdsenai-ascii-art.txt`
- [ ] Use `rich` to apply color scheme based on logo:
  - [ ] Rainbow gradient for the 'G' character (red→orange→yellow→green→blue→purple)
  - [ ] Blue/purple gradients for neural network fibers
  - [ ] White/gray for the text "GerdsenAI CLI"
- [ ] Add welcome message and version info
- [ ] Display startup animation/transition effect

**Commit Point 1: `feat: initial project structure and startup screen`**

## Phase 2: Configuration and LLM Client

### Task 4: Implement Configuration Management
- [ ] Create `gerdsenai_cli/config/settings.py`
- [ ] Use `pydantic` for configuration validation
- [ ] Define configuration schema:
  - [ ] LLM server URL (default: "http://localhost:11434")
  - [ ] Current model name
  - [ ] API timeout settings
  - [ ] User preferences (colors, verbosity)
- [ ] Create `gerdsenai_cli/config/manager.py`
- [ ] Implement first-run setup process:
  - [ ] Check for config file at `~/.config/gerdsenai_cli/settings.json`
  - [ ] If not found, prompt user for LLM server details
  - [ ] Validate connection before saving
  - [ ] Create config directory if needed
- [ ] Add configuration update methods

### Task 5: Develop LLM Client
- [ ] Create `gerdsenai_cli/core/llm_client.py`
- [ ] Implement `LLMClient` class with async methods:
  - [ ] `async def connect()` - Test connection to LLM server
  - [ ] `async def list_models()` - Get available models
  - [ ] `async def chat()` - Send chat completion request
  - [ ] `async def stream_chat()` - Stream responses for real-time display
- [ ] Use OpenAI-compatible API format for broad compatibility
- [ ] Add error handling and retry logic
- [ ] Implement connection pooling with `httpx`
- [ ] Add request/response logging for debugging

**Commit Point 2: `feat: add configuration management and LLM client`**

## Phase 3: Interactive Loop and Command Parser

### Task 6: Create Main Interactive Loop
- [ ] Implement `gerdsenai_cli/main.py` main function
- [ ] Create interactive prompt loop using `rich.prompt`
- [ ] Add custom prompt styling with GerdsenAI branding
- [ ] Implement graceful shutdown (Ctrl+C handling)
- [ ] Add session management and history

### Task 7: Implement Slash Command Parser
- [ ] Create `gerdsenai_cli/commands/parser.py`
- [ ] Implement command detection and routing
- [ ] Create base command class in `gerdsenai_cli/commands/base.py`
- [ ] Implement core commands:

#### `/help` Command
- [ ] Create `gerdsenai_cli/commands/help.py`
- [ ] Display available commands with descriptions
- [ ] Show usage examples
- [ ] Display current configuration status

#### `/exit` Command
- [ ] Create `gerdsenai_cli/commands/system.py`
- [ ] Implement graceful shutdown
- [ ] Save session data before exit

#### `/config` Command
- [ ] Create `gerdsenai_cli/commands/config.py`
- [ ] Subcommands:
  - [ ] `/config show` - Display current settings
  - [ ] `/config set <key> <value>` - Update setting
  - [ ] `/config reset` - Reset to defaults
  - [ ] `/config test` - Test LLM connection

#### `/model` Command
- [ ] Create `gerdsenai_cli/commands/model.py`
- [ ] Subcommands:
  - [ ] `/model list` - Show available models
  - [ ] `/model select <name>` - Switch to specific model
  - [ ] `/model info` - Show current model details

**Commit Point 3: `feat: implement interactive loop and command parser`**

## Phase 4: Core Agentic Features

### Task 8: Implement Project Context Awareness
- [ ] Create `gerdsenai_cli/core/context_manager.py`
- [ ] Implement `ProjectContext` class:
  - [ ] `scan_directory()` - Build file tree structure
  - [ ] `read_file_content()` - Read and cache file contents
  - [ ] `get_relevant_files()` - Filter files based on context
  - [ ] `build_context_prompt()` - Generate context for LLM
- [ ] Add file type detection and filtering
- [ ] Implement intelligent file selection (ignore binaries, logs, etc.)
- [ ] Add gitignore support
- [ ] Cache file contents for performance

### Task 9: Integrate Agentic Logic
- [ ] Create `gerdsenai_cli/core/agent.py`
- [ ] Implement `Agent` class:
  - [ ] Process user prompts with project context
  - [ ] Parse LLM responses for action intents
  - [ ] Handle conversation flow and state
- [ ] Define action intent schema:
  - [ ] `edit_file` - File modification requests
  - [ ] `create_file` - New file creation
  - [ ] `execute_command` - Terminal command execution
  - [ ] `explain_code` - Code explanation requests
- [ ] Implement intent parsing and validation

### Task 10: Implement File Editing Capabilities
- [ ] Create `gerdsenai_cli/core/file_editor.py`
- [ ] Implement `FileEditor` class:
  - [ ] `preview_changes()` - Show diff before applying
  - [ ] `apply_changes()` - Write changes to disk
  - [ ] `backup_file()` - Create backup before editing
  - [ ] `undo_changes()` - Revert to backup
- [ ] Add rich diff display with syntax highlighting
- [ ] Implement user confirmation prompts
- [ ] Add file watching for external changes

### Task 11: Implement Terminal Integration
- [ ] Create `gerdsenai_cli/core/terminal.py`
- [ ] Implement `TerminalExecutor` class:
  - [ ] `execute_command()` - Run shell commands safely
  - [ ] `stream_output()` - Real-time command output
  - [ ] `check_safety()` - Validate command safety
- [ ] Add command whitelist/blacklist
- [ ] Implement user confirmation for dangerous commands
- [ ] Add command history and logging

**Commit Point 4: `feat: add core agentic features and file editing`**

## Phase 5: Advanced Features

### Task 12: Add MCP Server Support
- [ ] Research Model Context Protocol (MCP) integration
- [ ] Create `gerdsenai_cli/core/mcp_client.py`
- [ ] Implement MCP server discovery and connection
- [ ] Add `/mcp` command for server management

### Task 13: Enhanced Command Set
- [ ] Add `/history` - Show conversation history
- [ ] Add `/clear` - Clear current session
- [ ] Add `/save` - Save conversation to file
- [ ] Add `/load` - Load previous conversation
- [ ] Add `/status` - Show system status
- [ ] Add `/debug` - Toggle debug mode

### Task 14: Performance Optimizations
- [ ] Implement async processing for better responsiveness
- [ ] Add caching for LLM responses
- [ ] Optimize file reading and context building
- [ ] Add progress indicators for long operations

**Commit Point 5: `feat: add advanced features and optimizations`**

## Phase 6: Testing and Documentation

### Task 15: Testing Suite
- [ ] Create `tests/` directory structure
- [ ] Add unit tests for core components
- [ ] Add integration tests for LLM client
- [ ] Add command parsing tests
- [ ] Add configuration management tests
- [ ] Set up GitHub Actions for CI/CD

### Task 16: Documentation
- [ ] Update `README.md` with GerdsenAI CLI information
- [ ] Add installation instructions
- [ ] Create user guide with examples
- [ ] Add developer documentation
- [ ] Create troubleshooting guide

### Task 17: Packaging and Distribution
- [ ] Configure `pyproject.toml` for PyPI distribution
- [ ] Add console entry points
- [ ] Create installation scripts
- [ ] Add version management automation
- [ ] Test installation on different platforms

**Commit Point 6: `feat: add testing, documentation, and packaging`**

## Future Enhancements

### Task 18: Extended Integrations
- [ ] Add support for multiple LLM providers
- [ ] Implement plugin system for extensions
- [ ] Add web interface option
- [ ] Integration with popular IDEs
- [ ] Add collaboration features

### Task 19: AI Model Management
- [ ] Add model download/update capabilities
- [ ] Implement model performance benchmarking
- [ ] Add custom fine-tuning support
- [ ] Model switching optimization

**Final Commit: `feat: complete GerdsenAI CLI v1.0 release`**

## Development Notes

- **Code Quality**: Use type hints throughout, follow PEP 8, and maintain 90%+ test coverage
- **Dependencies**: Only use actively maintained packages with recent updates
- **Security**: Validate all user inputs and implement safe command execution
- **Performance**: Target <500ms response time for most operations
- **Compatibility**: Support Python 3.11+ on Windows, macOS, and Linux
- **Documentation**: Maintain inline documentation and update README with each major feature

## Architecture Overview

```
gerdsenai_cli/
├── __init__.py
├── cli.py                 # Entry point
├── main.py               # Main application logic
├── commands/             # Slash command implementations
│   ├── __init__.py
│   ├── base.py
│   ├── config.py
│   ├── help.py
│   ├── model.py
│   └── system.py
├── config/               # Configuration management
│   ├── __init__.py
│   ├── manager.py
│   └── settings.py
├── core/                 # Core business logic
│   ├── __init__.py
│   ├── agent.py
│   ├── context_manager.py
│   ├── file_editor.py
│   ├── llm_client.py
│   └── terminal.py
└── utils/                # Utility functions
    ├── __init__.py
    ├── display.py
    └── helpers.py
