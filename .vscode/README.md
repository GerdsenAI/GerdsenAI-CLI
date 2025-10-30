# GerdsenAI CLI - VS Code Configuration

This directory contains VS Code configuration for a repeatable, high-quality development experience.

## 📋 Quick Start

1. **Install Recommended Extensions**
   - Press `Cmd+Shift+P` → "Extensions: Show Recommended Extensions"
   - Click "Install All"

2. **Activate Virtual Environment**
   - Run task: `✅ Check Venv`
   - Or manually: `source .venv/bin/activate`

3. **Start Development**
   - Press `Cmd+Shift+B` to run default build task (Start App)
   - Or press `Cmd+Shift+P` → "Tasks: Run Task" to see all options

## 🎯 Available Tasks

### Running the App
- **🚀 Start App (TUI)** - Launch in normal TUI mode (default: `Cmd+Shift+B`)
- **⚡ Start App (LLVL Mode)** - Launch in "Livin' La Vida Loca" mode
- **🛑 Stop App** - Stop GerdsenAI processes
- **🛑 Stop All Python Processes** - Nuclear option (kills all Python)

### Testing
- **🧪 Run All Tests** - Execute full test suite (default test task)
- **🧪 Run Tests with Coverage** - Generate HTML coverage report
- **🧪 Run Single Test File** - Test currently open file
- **📊 Show Coverage Report** - Open coverage HTML in browser

### Code Quality
- **✨ Format Code (Ruff)** - Auto-format all code
- **🔍 Lint Code (Ruff)** - Fix linting issues
- **🔍 Type Check (MyPy)** - Run type checker
- **🔧 Full QA Suite** - Run format → lint → type check → tests

### Maintenance
- **🧹 Clean Cache & Build Files** - Remove __pycache__, .pytest_cache, etc.
- **📦 Install Dependencies** - Install/reinstall all dependencies
- **🔄 Update Dependencies** - Update to latest versions
- **✅ Check Venv** - Verify virtual environment setup

## 🐛 Debugging

Press `F5` or use the Debug panel to launch:

- **🐛 Debug GerdsenAI CLI (TUI)** - Debug the main TUI application
- **🐛 Debug GerdsenAI CLI (LLVL Mode)** - Debug in LLVL mode
- **🐛 Debug Current Test File** - Debug the open test file
- **🐛 Debug All Tests** - Debug entire test suite
- **🐛 Debug with Python** - Debug any Python file

Set breakpoints by clicking in the gutter (left of line numbers).

## ⌨️ Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Cmd+Shift+B` | Start App (default build task) |
| `Cmd+Shift+T` | Run All Tests (default test task) |
| `F5` | Start Debugging |
| `Shift+F5` | Stop Debugging |
| `Cmd+Shift+P` | Command Palette (access all tasks) |
| `Cmd+Shift+E` | Explorer sidebar |
| `Cmd+Shift+X` | Extensions sidebar |
| `Cmd+J` | Toggle terminal |
| `Ctrl+` ` | Toggle terminal |

## 🔧 Settings Highlights

### Automatic Formatting
- **On Save**: Code auto-formats with Ruff
- **On Save**: Imports auto-organize
- **On Save**: Linting fixes auto-apply

### Testing
- **Auto-discover**: Tests found automatically on save
- **Pytest Integration**: Full pytest support with decorators

### Python Environment
- **Auto-activate**: Virtual environment activates in terminal
- **Default Interpreter**: Always uses `.venv/bin/python3.13`

### File Watching
- **Excluded**: `__pycache__`, `.venv`, cache directories (better performance)
- **Hidden**: Build artifacts, cache files (cleaner explorer)

## 📦 Recommended Extensions

All recommended extensions are listed in `extensions.json`. Install them for:
- Python development (Pylance, debugpy)
- Code quality (Ruff, MyPy)
- Testing (Test Explorer)
- Git integration (GitLens)
- AI assistance (GitHub Copilot)
- Documentation (Markdown tools)

## 🎨 Code Snippets

Type these prefixes and press Tab:

- `gatest` - Create async test function
- `gacmd` - Create command class
- `galog` - Add logger import
- `gaasync` - Create async function
- `gatry` - Try-except block with logging

## 🔄 Keeping Config in Sync

This configuration is version-controlled. After pulling changes:

1. Check if new extensions are recommended
2. Reload window if settings changed (`Cmd+Shift+P` → "Reload Window")
3. Run `✅ Check Venv` to verify environment

## 📚 Documentation

- [Main README](../README.md)
- [Contributing Guide](../docs/development/CONTRIBUTING.md)
- [Testing Guide](../docs/development/TESTING_GUIDE.md)
- [Full Documentation](../docs/README.md)

## 🆘 Troubleshooting

**Problem**: Tasks show "command not found"
- **Solution**: Run `✅ Check Venv` to verify virtual environment

**Problem**: Tests not discovered
- **Solution**: Reload window (`Cmd+Shift+P` → "Reload Window")

**Problem**: Debugger won't attach
- **Solution**: Make sure `debugpy` is installed: `pip install debugpy`

**Problem**: Ruff/MyPy not working
- **Solution**: Install dev dependencies: Run task `📦 Install Dependencies`

**Problem**: "source: command not found" on Windows
- **Solution**: Tasks are designed for macOS/Linux. On Windows, use `.venv\Scripts\activate`

## 🎯 Best Practices

1. **Always use tasks** instead of manual terminal commands
2. **Run Full QA Suite** before committing
3. **Use code snippets** for consistency
4. **Set breakpoints** when debugging instead of print statements
5. **Check coverage** to ensure adequate test coverage

---

Made with ❤️ by the GerdsenAI team
