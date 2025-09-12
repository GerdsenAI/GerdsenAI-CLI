# GerdsenAI CLI

A terminal-based agentic coding tool that connects to local AI models for intelligent code assistance.

## 🚀 Features

### Core Capabilities
- **AI-Powered Code Assistant** - Natural language interaction with local LLM models
- **Project Context Awareness** - Intelligent file scanning and context building
- **Safe File Operations** - AI-assisted editing with diff previews and automatic backups
- **Terminal Integration** - Secure command execution with user confirmation
- **Session Management** - Save and restore conversation sessions

### Command Categories
- **System Tools** - Configuration, status, help, and debugging
- **File Operations** - Browse, read, edit, create, and search project files
- **AI Agent** - Chat, context management, and agent statistics
- **Model Management** - Switch between LLM models and view model info
- **Terminal Integration** - Safe command execution and history management

## 📋 Requirements

- **Python 3.11+** (required)
- **Local LLM Server** - Ollama, LocalAI, or OpenAI-compatible API
- **Virtual Environment** - Recommended for development

## 🛠 Installation

### Quick Install (Recommended)
```bash
# Clone the repository
git clone https://github.com/GerdsenAI-Admin/GerdsenAI-CLI.git
cd GerdsenAI-CLI

# Create virtual environment
python3.11 -m venv .venv --prompt "gerdsenai-cli"
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

# Install in development mode
pip install -e .
```

### Future PyPI Installation
```bash
# Coming soon
pipx install gerdsenai-cli  # Recommended
# or
pip install gerdsenai-cli
```

## 🚀 Quick Start

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

See [TODO.md](TODO.md) for detailed development roadmap.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Follow the existing code style and patterns
4. Add tests for new functionality
5. Update documentation as needed
6. Submit a pull request

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
- Report issues: https://github.com/GerdsenAI-Admin/GerdsenAI-CLI/issues

---

**Happy coding with GerdsenAI! 🚀**
