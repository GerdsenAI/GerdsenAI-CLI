# GerdsenAI CLI Slash Commands Reference

This document provides a comprehensive reference for all available slash commands in the GerdsenAI CLI.

## Quick Start

- Type any command starting with `/` followed by the command name
- Use `/help` to see all available commands
- Use `/help <command>` for detailed help on a specific command
- Commands support autocompletion - press Tab while typing

## Command Categories

### 🤖 Agent Commands
Commands for interacting with the AI agent and managing conversations.

| Command | Aliases | Description | Usage |
|---------|---------|-------------|-------|
| `/agent` | `/a` | Show agent statistics and status | `/agent` |
| `/chat` | `/c` | Start or continue conversation with AI | `/chat <message>` |
| `/clear` | `/reset` | Clear conversation history and start fresh | `/clear` |
| `/refresh` | `/r` | Refresh project context for AI understanding | `/refresh` |

### 📁 File Commands
Commands for file operations and project management.

| Command | Aliases | Description | Usage |
|---------|---------|-------------|-------|
| `/files` | `/ls`, `/list` | List files and directories | `/files [path]` |
| `/read` | `/cat`, `/view` | Read and display file contents | `/read <file> [lines]` |
| `/edit` | `/modify` | Edit a file with AI assistance | `/edit <file>` |
| `/create` | `/new` | Create a new file | `/create <file> [template]` |
| `/search` | `/find`, `/grep` | Search for text across project files | `/search <term> [path]` |

### 🧠 Model Commands
Commands for managing AI models and connections.

| Command | Aliases | Description | Usage |
|---------|---------|-------------|-------|
| `/models` | `/model-list` | List available AI models | `/models` |
| `/model` | `/switch` | Switch to a different AI model | `/model <name>` |
| `/health` | `/ping` | Check AI model server health | `/health` |

### ⚙️ System Commands
Commands for system configuration and information.

| Command | Aliases | Description | Usage |
|---------|---------|-------------|-------|
| `/help` | `/h`, `/?` | Show available commands or help for specific command | `/help [command]` |
| `/about` | `/version`, `/info` | Show version and system information | `/about` |
| `/config` | `/settings` | Show current configuration | `/config [key] [value]` |
| `/status` | `/stat` | Show system status and diagnostics | `/status` |
| `/tools` | `/commands` | List all available tools with filtering | `/tools [category]` |
| `/init` | `/setup` | Initialize project with GerdsenAI guide | `/init` |
| `/copy` | `/clipboard` | Copy last output to clipboard | `/copy` |

### 💻 Terminal Commands
Commands for executing terminal operations safely.

| Command | Aliases | Description | Usage |
|---------|---------|-------------|-------|
| `/run` | `/exec`, `/cmd` | Execute a terminal command safely | `/run <command>` |
| `/history` | `/hist` | Show command execution history | `/history [count]` |
| `/pwd` | `/dir` | Show current working directory | `/pwd` |
| `/terminal-status` | `/term` | Show terminal executor status | `/terminal-status` |

## Detailed Command Reference

### Agent Commands

#### `/agent` - Agent Statistics
Shows detailed statistics about the AI agent including:
- Current model information
- Conversation metrics
- Context analysis stats
- Performance data

**Example:**
```
/agent
```

#### `/chat <message>` - Conversational AI
Engage in natural conversation with the AI agent. The agent maintains context and can help with coding tasks.

**Examples:**
```
/chat How do I optimize this function?
/chat Explain the decorator pattern
/c What files should I look at first?
```

#### `/clear` - Reset Session
Clears the conversation history and resets the agent context. Useful for starting fresh on a new topic.

**Example:**
```
/clear
```

#### `/refresh` - Update Context
Forces the agent to rescan the project and update its understanding of your codebase.

**Example:**
```
/refresh
```

### File Commands

#### `/files [path]` - List Directory Contents
Lists files and directories, with optional path specification.

**Examples:**
```
/files                    # List current directory
/files src/               # List src directory
/ls gerdsenai_cli/        # Using alias
```

#### `/read <file> [lines]` - Read File Contents
Displays the contents of a file with optional line range specification.

**Examples:**
```
/read main.py             # Read entire file
/read config.py 1-20      # Read lines 1-20
/cat README.md            # Using alias
```

#### `/edit <file>` - Edit File
Opens a file for AI-assisted editing with diff preview and safety checks.

**Examples:**
```
/edit main.py
/modify src/config.py
```

#### `/create <file> [template]` - Create New File
Creates a new file with optional template specification.

**Examples:**
```
/create utils.py
/create components/Header.jsx react-component
/new tests/test_api.py pytest
```

#### `/search <term> [path]` - Search Files
Searches for text across project files with optional path restriction.

**Examples:**
```
/search "TODO"            # Search entire project
/search "class" src/      # Search in src directory
/grep "async def"         # Using alias
```

### Model Commands

#### `/models` - List Available Models
Shows all AI models available on the configured server.

**Example:**
```
/models
```

#### `/model <name>` - Switch Model
Changes the active AI model for conversations.

**Examples:**
```
/model llama3.1:8b
/switch codellama:13b
```

#### `/health` - Check Model Health
Tests connectivity and health of the AI model server.

**Example:**
```
/health
```

### System Commands

#### `/help [command]` - Show Help
Displays general help or specific command documentation.

**Examples:**
```
/help                     # Show all commands
/help search              # Help for search command
/?                        # Using alias
```

#### `/about` - System Information
Shows version, build information, and system details.

**Example:**
```
/about
```

#### `/config [key] [value]` - Configuration
Shows current configuration or updates specific settings.

**Examples:**
```
/config                   # Show all config
/config api_url           # Show specific value
/config timeout 30        # Set new value
```

#### `/status` - System Status
Displays comprehensive system status including performance metrics.

**Example:**
```
/status
```

#### `/tools [category]` - List Tools
Shows available tools with optional category filtering.

**Examples:**
```
/tools                    # Show all tools
/tools agent              # Show agent tools only
/tools --detailed         # Detailed view
```

### Terminal Commands

#### `/run <command>` - Execute Command
Safely executes terminal commands with validation and confirmation.

**Examples:**
```
/run ls -la
/run pytest tests/
/exec npm test
```

#### `/history [count]` - Command History
Shows recent command execution history.

**Examples:**
```
/history                  # Show recent commands
/history 10               # Show last 10 commands
```

#### `/pwd` - Working Directory
Shows the current working directory.

**Example:**
```
/pwd
```

## Command Features

### Auto-completion
- Press Tab while typing commands for auto-completion
- Works with command names and common file paths
- Supports partial matches

### Command History
- Use Up/Down arrows to navigate command history
- History persists between sessions
- Search history with Ctrl+R

### Error Handling
- Commands validate input before execution
- Clear error messages with suggestions
- Safe defaults for potentially dangerous operations

### Context Awareness
- Commands understand project structure
- File operations respect .gitignore patterns
- Smart path resolution and suggestions

## Tips for Effective Usage

### Getting Started
1. Use `/refresh` when starting work on a project
2. Ask questions with `/chat` to understand the codebase
3. Use `/files` to explore project structure
4. Check `/status` if experiencing issues

### Development Workflow
1. `/refresh` - Update project context
2. `/search` - Find relevant code
3. `/read` - Examine specific files
4. `/edit` - Make changes with AI assistance
5. `/run` - Test changes safely

### Troubleshooting
- Use `/health` to check AI model connectivity
- Use `/status` for system diagnostics
- Use `/about` for version information
- Use `/config` to verify settings

### Performance Tips
- Use specific paths with file commands when possible
- Limit search scope for better performance
- Use `/clear` to reset if context becomes too large
- Regular `/refresh` keeps context current

## Security and Safety

### Command Validation
- All commands are validated before execution
- Potentially dangerous operations require confirmation
- File operations respect project boundaries

### Safe Execution
- Terminal commands are sandboxed
- Automatic backups before file modifications
- Rollback capabilities for changes
- Read-only mode for sensitive operations

### Container Security
- Development happens in isolated container environment
- Network access controlled by firewall rules
- Configurable security levels (strict/development/testing)
- Volume isolation for data persistence

---

For additional help or to report issues, use `/help` or check the project documentation.
