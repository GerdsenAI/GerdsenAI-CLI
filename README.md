# GerdsenAI CLI

[![Python Version](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![Code Coverage](https://img.shields.io/badge/coverage-90%25-brightgreen.svg)](htmlcov/index.html)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-passing-brightgreen.svg)](tests/)

A terminal-based agentic coding tool that connects to local AI models for intelligent code assistance.

---

> **⚠️ IMPORTANT: Virtual Environment Required**
> 
> **Always use the project virtual environment:** `.venv`
> ```bash
> source .venv/bin/activate  # Required before ANY command
> ```
> See [Virtual Environment Setup](#-virtual-environment-setup) for details.

---

## 🚀 Features

### Core Capabilities
- **AI-Powered Code Assistant** - Natural language interaction with local LLM models
- **Project Context Awareness** - Intelligent file scanning and context building
- **Safe File Operations** - AI-assisted editing with diff previews and automatic backups
- **Terminal Integration** - Secure command execution with user confirmation
- **Conversation Management** - Save, load, and export conversations (`/save`, `/load`, `/export`)
- **Interactive TUI Mode** - Enhanced terminal UI with real-time streaming and conversation history

### Command Categories
- **System Tools** - Configuration, status, help, and debugging
- **File Operations** - Browse, read, edit, create, and search project files
- **AI Agent** - Chat, context management, and agent statistics
- **Model Management** - Switch between LLM models and view model info
- **Terminal Integration** - Safe command execution and history management

## 📋 Requirements

- **Python 3.11+** (required, currently using 3.11.13)
  - Supported versions: 3.11, 3.12, 3.13
  - Virtual environment uses Python 3.11.13
- **Local LLM Server** - Ollama, LocalAI, or OpenAI-compatible API
- **Virtual Environment** - `.venv` (mandatory for development)

## 🛠 Installation

### � From PyPI (Recommended)
```bash
# Install with pipx (isolated, recommended)
pipx install gerdsenai-cli

# Or install with pip
pip install gerdsenai-cli

# Verify installation
gerdsenai --version
```

### 🔧 Development Installation

**🚨 CRITICAL: You MUST use the project's `.venv` virtual environment**

```bash
# 1. Clone the repository
git clone https://github.com/GerdsenAI/GerdsenAI-CLI.git
cd GerdsenAI-CLI

# 2. Create virtual environment (if it doesn't exist)
python3.11 -m venv .venv

# 3. ACTIVATE the virtual environment (REQUIRED)
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

# 4. Verify you're in the venv
which python  # Should show: <project-path>/.venv/bin/python
echo $VIRTUAL_ENV  # Should show: <project-path>/.venv

# 5. Install in development mode
pip install -e ".[dev]"

# 6. Verify installation
python -c "from gerdsenai_cli.commands.system import HelpCommand; print('✅ Import successful')"
gerdsenai --version
```

**⚠️ Common Mistakes to Avoid:**
- ❌ Running `pip install` without activating venv
- ❌ Using system Python at `/opt/homebrew/bin/python3`
- ❌ Using `--break-system-packages` flag
- ❌ Installing with homebrew's pip
- ✅ **ALWAYS** `source .venv/bin/activate` first

### 🏗️ Alternative Installation Methods
```bash
# Install from source (latest)
pip install git+https://github.com/GerdsenAI/GerdsenAI-CLI.git

# Install specific branch/tag
pip install git+https://github.com/GerdsenAI/GerdsenAI-CLI.git@main
```

## � Virtual Environment Setup

### Why Virtual Environment is Mandatory

**Problem:** System Python installations cause dependency conflicts, version mismatches, and "module not found" errors.

**Solution:** Use the project's dedicated `.venv` virtual environment.

### Quick Setup

```bash
# Navigate to project
cd GerdsenAI-CLI

# Activate venv (do this EVERY time you work on the project)
source .venv/bin/activate

# Verify activation
echo $VIRTUAL_ENV  # Should show: <project-path>/.venv
which python       # Should show: <project-path>/.venv/bin/python
```

### Creating venv (First Time Only)

```bash
# If .venv doesn't exist
python3.11 -m venv .venv

# Activate it
source .venv/bin/activate

# Install dependencies
pip install -e ".[dev]"
```

### Troubleshooting

**Q: How do I know if venv is active?**
```bash
# Check these indicators:
echo $VIRTUAL_ENV        # Shows path if active
which python             # Should point to .venv/bin/python
python --version         # Should match venv Python (3.11.x or 3.13.x)

# Your prompt should also show: (.venv) in front
```

**Q: I see "module not found" errors**
```bash
# 1. Ensure venv is active
source .venv/bin/activate

# 2. Reinstall in editable mode
pip install -e ".[dev]"

# 3. Verify
python -c "import gerdsenai_cli; print('OK')"
```

**Q: Commands fail with ImportError**
```bash
# DON'T use system Python
❌ /opt/homebrew/bin/python3 -m gerdsenai_cli

# DO use venv Python
✅ source .venv/bin/activate
✅ python -m gerdsenai_cli
```

### Best Practices

1. **Always activate venv first**: `source .venv/bin/activate`
2. **One venv per project**: Don't mix projects
3. **Keep it updated**: `pip install --upgrade pip`
4. **Never commit .venv**: Already in `.gitignore`
5. **Document venv location**: `.venv/README.md` has setup instructions

### VS Code Integration

The project is configured to use `.venv` automatically:
- `.vscode/settings.json` points to `.venv/bin/python`
- Tests run in venv automatically
- Terminal activates venv on open

## �🚀 Quick Start

1. **Start the CLI**
   ```bash
   gerdsenai
   # or
   python -m gerdsenai_cli
   ```

2. **First-time Setup**
   - The CLI will automatically prompt for LLM server configuration
   - Default: `http://localhost:11434` (Ollama)
   - Test connection and select an available model

3. **Basic Usage**
   ```bash
   # Get help
   /help

   # List available tools
   /tools

   # Browse project files
   /ls

   # Start coding with AI assistance
   What files should I look at to understand this project?

   # Edit files with AI help
   /edit main.py "add error handling to the main function"
   ```

4. **Interactive Streaming Responses**
   - By default, responses stream token-by-token for a more natural experience.
   - Disable streaming at runtime by toggling the preference in a future config command, or edit your settings file to set `"streaming": false` under `user_preferences`.
   - If streaming encounters an error, the CLI automatically falls back to standard full-response mode.

## 📚 Key Commands

### Essential Commands
- `/help` - Show all available commands
- `/tools` - List tools by category with search/filter
- `/status` - Check system and AI connection status
- `/about` - Version and troubleshooting information

### File Operations
- `/ls [path]` - List files in project directory
- `/cat <file>` - Read and display file contents
- `/edit <file> "description"` - AI-assisted file editing
- `/create <file> "description"` - Create new files
- `/search <pattern>` - Search across project files

### AI & Context
- Chat naturally or use `/chat <message>`
- `/agent` - View AI agent statistics
- `/refresh` - Refresh project context
- `/clear` - Clear conversation history

### Models & Configuration
- `/models` - List available AI models
- `/model <name>` - Switch to specific model
- `/config` - Show current configuration
- `/setup` - Reconfigure LLM server connection

## 🏗 Architecture

GerdsenAI CLI uses a modular, agent-based architecture:

```
gerdsenai_cli/
├── cli.py                 # Entry point
├── main.py               # Main application logic
├── commands/             # Slash command implementations
│   ├── agent.py         # AI agent commands
│   ├── files.py         # File operation commands
│   ├── model.py         # Model management commands
│   ├── system.py        # System commands
│   └── terminal.py      # Terminal integration commands
├── core/                # Core business logic
│   ├── agent.py         # AI agent orchestration
│   ├── context_manager.py  # Project context analysis
│   ├── file_editor.py   # Safe file editing with backups
│   ├── llm_client.py    # LLM communication
│   └── terminal.py      # Terminal command execution
├── config/              # Configuration management
└── utils/               # Utilities and display helpers
```

## 🔧 Development

### Setup Development Environment
```bash
# Create virtual environment
python3.11 -m venv .venv --prompt "gerdsenai-cli"
source .venv/bin/activate

# Install in editable mode
pip install -e .

# Verify installation
python -c "from gerdsenai_cli.commands.system import HelpCommand; print('✅ Import successful')"
```

### Code Quality Tools
```bash
# Linting and formatting
ruff check gerdsenai_cli/
ruff format gerdsenai_cli/

# Type checking
mypy gerdsenai_cli/

# Run tests
pytest
```

### Project Status
- **Phase 1-7**: ✅ **Complete** - Core functionality, commands, and agent features
- **Phase 8+**: 🚧 **Planned** - Extended commands, integrations, and advanced features

See [docs/TODO.md](docs/TODO.md) for detailed development roadmap.

## 📚 Documentation

Comprehensive documentation is available in the `docs/` directory:

### Quick Links
- **[Documentation Hub](docs/README.md)** - Central documentation index
- **[Contributing Guide](docs/development/CONTRIBUTING.md)** - How to contribute
- **[Testing Guide](docs/development/TESTING_GUIDE.md)** - Running and writing tests
- **[Feature Documentation](docs/features/)** - Detailed feature documentation
- **[Example Configs](examples/)** - Sample configuration files

### Configuration Examples
Ready-to-use configuration examples in `examples/config/`:
- **[basic.json](examples/config/basic.json)** - Minimal setup for getting started
- **[power-user.json](examples/config/power-user.json)** - Advanced configuration
- **[mcp-github.json](examples/config/mcp-github.json)** - GitHub MCP integration

```bash
# Use an example config
python -m gerdsenai_cli --config examples/config/basic.json
```

See [examples/README.md](examples/README.md) for more details on configuration options.

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](docs/development/CONTRIBUTING.md) for detailed information.

**Quick Start for Contributors:**

1. Fork the repository
2. Create and activate virtual environment (`.venv`)
3. Install development dependencies: `pip install -e ".[dev]"`
4. Create a feature branch
5. Make your changes and add tests
6. Run tests: `pytest -v`
7. Update documentation as needed
8. Submit a pull request

**Important:** All development must be done in the project's virtual environment. See [.venv/README.md](.venv/README.md) for details.

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🐛 Troubleshooting

### Common Issues
- **Import Errors**: Ensure virtual environment is activated and `pip install -e .` was run
- **LLM Connection**: Check `/status` and use `/setup` to reconfigure server
- **Slow Performance**: Use `/refresh` to optimize project context

### Getting Help
- Use `/about` to gather system information for bug reports
- Check `/status --verbose` for detailed diagnostics
- Report issues: https://github.com/GerdsenAI/GerdsenAI-CLI/issues

---

**Happy coding with GerdsenAI! 🚀**
