# GerdsenAI CLI Documentation

Welcome to the GerdsenAI CLI documentation hub! This directory contains all project documentation organized by topic.

---

> **⚠️ IMPORTANT: Virtual Environment Required**
> 
> **Always activate the virtual environment before development:**
> ```bash
> source .venv/bin/activate
> ```
> See [Virtual Environment Setup](../.venv/README.md) for details.

---

## 📚 Documentation Structure

### 🚀 Getting Started
- **[Main README](../README.md)** - Project overview, installation, and quick start
- **[Quick Start Guide](development/QUICK_START_IMPLEMENTATION.md)** - Fast track to getting started
- **[Contributing Guide](development/CONTRIBUTING.md)** - How to contribute to the project

### 🛠 Development
- **[Testing Guide](development/TESTING_GUIDE.md)** - How to run and write tests
- **[Security Improvements](development/SECURITY_IMPROVEMENTS.md)** - Security best practices
- **[Conversation Commands](development/CONVERSATION_COMMANDS.md)** - Available slash commands
- **[Slash Commands](development/SLASH_COMMAND.MD)** - Detailed slash command reference
- **[Next Steps Planning](development/NEXT_STEPS_PLANNING.md)** - Future development roadmap

### ✨ Features
- **[Feature Test Summary](features/FEATURE_TEST_SUMMARY.md)** - Comprehensive feature testing results
- **[Feature Complete](features/FEATURE_COMPLETE.md)** - Feature completion status
- **[Implementation Complete](features/IMPLEMENTATION_COMPLETE.md)** - Implementation milestones
- **[TUI Integration](features/TUI_INTEGRATION_COMPLETE.md)** - Terminal UI integration details
- **[Enhanced TUI](features/ENHANCED_TUI_IMPLEMENTATION.md)** - Enhanced UI features
- **[Animation System](features/ANIMATION_SYSTEM_IMPLEMENTATION.md)** - Animation system documentation
- **[Conversation I/O](features/CONVERSATION_IO_IMPLEMENTATION.md)** - Conversation save/load features

### 📋 Implementation History
- **[Phase 1: Auto-scroll](features/PHASE_1_AUTO_SCROLL_IMPLEMENTATION.md)** - Auto-scrolling implementation
- **[Phase 1: Prompt Toolkit](features/PHASE_1_PROMPT_TOOLKIT_COMPLETE.md)** - Prompt toolkit integration
- **[Phase 1: Visual Tests](features/PHASE_1_VISUAL_TEST_RESULTS.md)** - Visual testing results
- **[Phase 8B Test Report](features/PHASE_8B_TEST_REPORT.md)** - Phase 8B testing documentation
- **[Layout Reorganization](features/LAYOUT_REORGANIZATION_SUMMARY.md)** - Layout restructuring summary
- **[De-containerization](features/DE_CONTAINERIZATION_SUMMARY.md)** - Container removal summary
- **[TODO Updates](features/TODO_UPDATE_SUMMARY.md)** - TODO list management changes

### 📊 Status & Analysis
- **[Alignment Analysis](features/ALIGNMENT_ANALYSIS.md)** - Feature alignment analysis
- **[Session Summary](features/SESSION_SUMMARY_STATUS_MESSAGES.md)** - Session status messaging
- **[Status Message Integration](features/STATUS_MESSAGE_INTEGRATION.md)** - Status message implementation
- **[TUI Launch Status](features/TUI_LAUNCH_STATUS.md)** - TUI launch status tracking
- **[TUI Integration Summary](features/TUI_INTEGRATION_SUMMARY.md)** - TUI integration overview

### 🏗 Architecture
- **[Project Structure](../README.md#project-structure)** - Directory organization
- **[Virtual Environment](../.venv/README.md)** - Venv configuration and usage

### 📝 Project Management
- **[TODO](TODO.md)** - Current TODO items and task tracking
- **[Claude AI Notes](CLAUDE.md)** - AI assistant conversation context

---

## 🔍 Quick Reference

### Common Tasks

#### Running Tests
```bash
source .venv/bin/activate
pytest -v                        # All tests
pytest tests/test_tui.py -v     # Specific test file
python scripts/check_venv.py    # Verify venv setup
```

#### Running the CLI
```bash
source .venv/bin/activate
python -m gerdsenai_cli          # Start TUI mode
python -m gerdsenai_cli --help   # Show help
```

#### Code Quality
```bash
source .venv/bin/activate
ruff check gerdsenai_cli/        # Lint code
ruff format gerdsenai_cli/       # Format code
mypy gerdsenai_cli/              # Type checking
```

### Slash Commands (In TUI)
- `/help` - Show available commands
- `/status` - Show system status
- `/model` - Switch AI model
- `/thinking` - Toggle thinking display
- `/save` - Save conversation
- `/load` - Load conversation
- `/export` - Export conversation
- `/mcp` - MCP server management
- `/clear` - Clear conversation
- `/exit` or `/quit` - Exit application

---

## 📦 Package Structure

```
gerdsenai_cli/
├── __init__.py           # Package initialization
├── __main__.py           # Entry point
├── cli.py                # CLI setup
├── main.py               # Main application logic
├── commands/             # Command implementations
│   ├── agent.py         # AI agent commands
│   ├── files.py         # File operation commands
│   ├── intelligence.py  # Intelligence tracking
│   ├── mcp.py           # MCP server commands
│   ├── memory.py        # Memory management
│   ├── model.py         # Model management
│   ├── parser.py        # Command parser
│   ├── planning.py      # Planning commands
│   ├── system.py        # System commands
│   └── terminal.py      # Terminal commands
├── config/              # Configuration management
│   ├── manager.py       # Config manager
│   └── settings.py      # Settings model
├── core/                # Core functionality
│   ├── agent.py         # AI agent
│   ├── capabilities.py  # Model capabilities
│   ├── context_manager.py  # Context management
│   └── llm_client.py    # LLM client
├── ui/                  # User interface
│   └── prompt_toolkit_tui.py  # TUI implementation
└── utils/               # Utilities
    ├── backup.py        # Backup utilities
    ├── context.py       # Context utilities
    ├── file_ops.py      # File operations
    └── rich_converter.py  # Rich text conversion
```

---

## 🤝 Contributing

We welcome contributions! Please see:
1. **[Contributing Guide](development/CONTRIBUTING.md)** - Full contribution guidelines
2. **[Testing Guide](development/TESTING_GUIDE.md)** - How to test your changes
3. **[Security Guide](development/SECURITY_IMPROVEMENTS.md)** - Security best practices

### Before Contributing
- ✅ Activate virtual environment (`.venv`)
- ✅ Read the contributing guide
- ✅ Run tests to ensure everything works
- ✅ Follow code style guidelines

---

## 📄 License

This project is licensed under the MIT License. See the LICENSE file for details.

---

## 🔗 Links

- **GitHub Repository:** [GerdsenAI/GerdsenAI-CLI](https://github.com/GerdsenAI/GerdsenAI-CLI)
- **Issues:** [Report bugs or request features](https://github.com/GerdsenAI/GerdsenAI-CLI/issues)
- **Discussions:** [Join the community](https://github.com/GerdsenAI/GerdsenAI-CLI/discussions)

---

**Last Updated:** October 5, 2025
