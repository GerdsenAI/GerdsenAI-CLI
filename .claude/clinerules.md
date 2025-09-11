# GerdsenAI CLI Development Rules

Never use emojis in UI.Always think socratically, UI/UX should feel perfect for this terminal/CLI application, these rules ensure consistent development practices, package management, and local LLM optimization for the GerdsenAI CLI project.

## 📝 Commit Patterns

### Required Commit Format
- **Format**: `<type>: <description>`
- **Types**:
  - `feat:` - New features
  - `fix:` - Bug fixes
  - `chore:` - Maintenance tasks
  - `docs:` - Documentation updates
  - `refactor:` - Code restructuring
  - `test:` - Test additions/modifications

### Commit Rules
1. Use present tense, imperative mood ("add feature" not "added feature")
2. Keep first line under 72 characters
3. Capitalize first letter of description
4. No period at end of first line
5. Follow TODO.md commit points for major milestones

### Examples
- ✅ `feat: add streaming chat completion support`
- ✅ `fix: resolve model selection validation error`
- ✅ `chore: update dependencies to latest stable versions`
- ❌ `updated the thing` (no type, past tense)
- ❌ `feat: Added new feature.` (capitalized type, period)

## � Virtual Environment Management

### Python Version Requirements
1. **Minimum Version**: Python 3.11+ (required by pyproject.toml)
2. **Recommended**: Python 3.11.13+ (latest stable)
3. **Installation**: Use system package manager (homebrew on macOS)
   ```bash
   # macOS with Homebrew
   brew install python@3.11
   ```

### Virtual Environment Setup
1. **Create Virtual Environment**:
   ```bash
   # Using specific Python version (recommended)
   /opt/homebrew/bin/python3.11 -m venv .venv --prompt "gerdsenai-cli"

   # Or using system python (if 3.11+)
   python3 -m venv .venv --prompt "gerdsenai-cli"
   ```

2. **Activate Virtual Environment**:
   ```bash
   # macOS/Linux
   source .venv/bin/activate

   # Windows
   .venv\Scripts\activate
   ```

3. **Verify Environment**:
   ```bash
   # Check Python version
   python --version  # Should show 3.11+

   # Check pip location
   which pip  # Should point to .venv/bin/pip
   ```

### Development Installation
1. **Install in Editable Mode**:
   ```bash
   pip install -e .
   ```

2. **Verify Installation**:
   ```bash
   # Check package installation
   pip list | grep gerdsenai-cli

   # Test CLI entry point
   python -m gerdsenai_cli --version
   ```

### Environment Validation
1. **Required Dependencies Check**:
   ```bash
   # Verify Rich Console (common issue)
   python -c "from rich.console import Console; print('✅ Rich imported successfully')"

   # Verify Typer
   python -c "import typer; print('✅ Typer imported successfully')"

   # Verify all core imports
   python -c "from gerdsenai_cli.commands.system import HelpCommand; print('✅ System commands imported successfully')"
   ```

2. **Common Import Issues**:
   - **Rich Console errors**: Usually indicates missing or incorrect virtual environment
   - **Module not found**: Check if editable installation completed successfully
   - **Python version errors**: Verify Python 3.11+ is being used

### Virtual Environment Best Practices
1. **Directory Structure**:
   ```
   GerdsenAI-CLI/
   ├── .venv/                    # Virtual environment (gitignored)
   ├── gerdsenai_cli/           # Main package
   ├── pyproject.toml           # Dependencies and build config
   └── README.md                # Installation instructions
   ```

2. **Activation Workflow**:
   ```bash
   # Always activate before development
   source .venv/bin/activate

   # Install/update dependencies
   pip install -e .

   # Run development commands
   python -m gerdsenai_cli
   ```

3. **Environment Isolation**:
   - Never install project dependencies globally
   - Use separate virtual environments for different projects
   - Always verify which Python/pip is being used

### Troubleshooting Virtual Environment Issues

#### Issue: "Rich Console could not be resolved"
**Solution**: Recreate virtual environment with correct Python version
```bash
rm -rf .venv
/opt/homebrew/bin/python3.11 -m venv .venv --prompt "gerdsenai-cli"
source .venv/bin/activate
pip install -e .
```

#### Issue: "Module not found" errors
**Solution**: Verify editable installation
```bash
source .venv/bin/activate
pip uninstall gerdsenai-cli
pip install -e .
```

#### Issue: Python version conflicts
**Solution**: Use explicit Python 3.11 path
```bash
which python3.11  # Should show /opt/homebrew/bin/python3.11
python3.11 --version  # Should show 3.11.x
```

#### Issue: CLI only shows version, doesn't start interactive mode
**Diagnosis**: Usually indicates missing core modules or import errors
```bash
# Debug with verbose error reporting
source .venv/bin/activate
python -m gerdsenai_cli --debug
```

### Virtual Environment Maintenance
1. **Weekly**: Update pip and core tools
   ```bash
   pip install --upgrade pip setuptools wheel
   ```

2. **Monthly**: Recreate environment for fresh state
   ```bash
   rm -rf .venv
   /opt/homebrew/bin/python3.11 -m venv .venv --prompt "gerdsenai-cli"
   source .venv/bin/activate
   pip install -e .
   ```

3. **Before Commits**: Verify environment integrity
   ```bash
   source .venv/bin/activate
   python -c "import gerdsenai_cli; print('✅ Package imports correctly')"
   ```

## �📦 Package Management

### Dependency Requirements
1. **Python Version**: Minimum 3.11+ (as specified in pyproject.toml)
2. **Core Dependencies**: Only use actively maintained packages
3. **Version Pinning**: Use minimum versions with `>=` for flexibility

### Approved Core Dependencies
```toml
# Core framework (CLI)
typer>=0.9.0          # Modern CLI framework, actively maintained
rich>=13.7.0          # Terminal formatting, frequent updates

# HTTP and async
httpx>=0.25.2         # Modern async HTTP client
asyncio-compat>=0.2.0 # Note: Consider removing if not needed

# Data validation and config
pydantic>=2.5.0       # V2 is actively maintained, performant
python-dotenv>=1.0.0  # Environment management

# Cross-platform support
colorama>=0.4.6       # Terminal colors, stable
```

### Development Dependencies
```toml
# Testing
pytest>=7.4.0
pytest-asyncio>=0.21.0

# Code quality (use Ruff for consolidation)
ruff>=0.1.0          # Replaces flake8, isort, autoflake
black>=23.0.0        # Code formatting
mypy>=1.7.0          # Type checking
pre-commit>=3.5.0    # Git hooks
```

### Package Rules
1. **Review quarterly**: Check for deprecated packages
2. **Ruff preference**: Use Ruff to replace multiple tools (flake8, isort, etc.)
3. **Security updates**: Apply security patches immediately
4. **Version conflicts**: Resolve by updating to compatible versions
5. **Remove unused**: Audit and remove unused dependencies

### Deprecated/Avoid
- ❌ Old async libraries (prefer built-in asyncio)
- ❌ Unmaintained CLI frameworks (Click without Typer)
- ❌ Multiple formatting tools when Ruff can replace them

## 🤖 Local LLM Optimization

### Connection Optimization
1. **Connection Pooling**: Use httpx.AsyncClient for persistent connections
2. **Timeout Configuration**:
   - Default: 30s API timeout
   - Health checks: 5s timeout
   - Model listing: 10s timeout
3. **Retry Logic**: Maximum 3 retries with exponential backoff
4. **Multiple Endpoints**: Support fallback endpoints for different LLM servers

### Model Management
1. **Lazy Loading**: Only load models when needed
2. **Model Caching**: Cache model list for session duration
3. **Auto-Selection**: Fallback to first available model if none selected
4. **Model Validation**: Verify model exists before sending requests

### Memory and Performance
1. **Context Length**: Default max 4000 tokens, configurable
2. **Streaming**: Implement streaming for real-time responses
3. **Request Batching**: Group multiple requests when possible
4. **File Context**: Intelligent file filtering (ignore binaries, logs)
5. **Async Operations**: Use async/await throughout for non-blocking I/O

### LLM Server Compatibility
1. **OpenAI Compatible**: Primary API format
2. **Fallback Endpoints**: Support alternative API paths
3. **Error Handling**: Graceful fallback for different response formats
4. **Health Monitoring**: Regular health checks and status reporting

### Configuration Optimization
```python
# Optimized settings for local LLM
{
    "api_timeout": 30.0,
    "max_retries": 3,
    "max_context_length": 4000,
    "temperature": 0.7,
    "top_p": 0.9,
    "stream": true,  # Enable for real-time responses
    "keep_alive": true  # Maintain connection pool
}
```

## 🏗️ Architecture Rules

### File Structure Compliance
Follow the exact structure from TODO.md:
```
gerdsenai_cli/
├── __init__.py           # Version info
├── cli.py               # Entry point
├── main.py              # Main application logic
├── commands/            # Slash command implementations
├── config/              # Configuration management
├── core/                # Business logic (LLM, context, agent)
└── utils/               # Utility functions
```

### Code Quality Standards
1. **Type Hints**: Use throughout codebase (mypy strict mode)
2. **Pydantic Models**: For configuration and data validation
3. **Async/Await**: For all I/O operations
4. **Error Handling**: Comprehensive exception handling
5. **Logging**: Use structured logging with appropriate levels

### Development Phases
Refined implementation based on current state analysis:
1. **Phase 1**: Project scaffolding (✅ Complete)
2. **Phase 2**: Configuration and LLM client (✅ Complete)
3. **Phase 3**: Basic interactive loop (✅ Complete)
4. **Phase 4**: Core agentic features (🚧 **PRIORITY NOW**)
   - Context Manager for project awareness
   - File Editor for safe code modifications
   - Agent Logic for orchestrating AI actions
5. **Phase 5**: Enhanced command system (📅 Planned)
6. **Phase 6**: Terminal integration and advanced features (📅 Planned)
7. **Phase 7**: Testing and documentation (📅 Planned)

## 🔒 Security Rules

1. **Input Validation**: Validate all user inputs using Pydantic
2. **Command Safety**: Whitelist/blacklist for terminal commands
3. **File Access**: Respect gitignore and security boundaries
4. **API Keys**: Never log or expose API keys/tokens
5. **Safe Defaults**: Conservative settings for new features

## 🧪 Testing Requirements

1. **Coverage**: Minimum 80% test coverage
2. **Unit Tests**: For all core components
3. **Integration Tests**: LLM client and configuration
4. **Async Testing**: Use pytest-asyncio for async code
5. **Mock External**: Mock LLM server calls in tests

## 📚 Documentation Standards

1. **Docstrings**: Google-style docstrings for all functions
2. **Type Annotations**: Complete type hints
3. **README Updates**: Keep installation and usage current
4. **Inline Comments**: Explain complex logic, not obvious code
5. **TODO Comments**: Link to GitHub issues for tracking

## 🚀 Performance Targets

1. **Startup Time**: < 2 seconds to interactive prompt
2. **Response Time**: < 500ms for local operations
3. **Memory Usage**: < 100MB baseline memory footprint
4. **Model Loading**: < 5 seconds to load model list
5. **File Scanning**: < 1 second for typical project directories
6. **Context Building**: < 2 seconds for project analysis
7. **File Editing**: < 500ms for diff generation and validation

## 🎯 Current Implementation Priority

### Immediate Goals (Core Agentic Features)
1. **Context Manager** (`gerdsenai_cli/core/context_manager.py`)
   - Project file structure analysis
   - Intelligent file filtering (respect gitignore)
   - Context building for LLM understanding
   - File content caching and management

2. **File Editor** (`gerdsenai_cli/core/file_editor.py`)
   - Safe file modification with validation
   - Diff preview and user confirmation
   - Backup management and rollback
   - Syntax-aware editing capabilities

3. **Agent Logic** (`gerdsenai_cli/core/agent.py`)
   - Intent parsing from LLM responses
   - Action orchestration and validation
   - Context-aware decision making
   - Safe execution boundaries

### Implementation Strategy
- **Quality over Speed**: Robust, well-tested components
- **Safety First**: All file operations require validation/confirmation
- **Context Awareness**: AI must understand project structure
- **User Control**: Clear previews and confirmations for all changes

## 🔄 Maintenance Schedule

### Weekly
- Check for security updates
- Review open issues and PRs
- Update development dependencies

### Monthly
- Audit package dependencies
- Review and update documentation
- Performance profiling and optimization

### Quarterly
- Major dependency updates
- Security audit
- Performance benchmarking
- Architecture review

## ⚡ Quick Reference

### Before Every Commit
1. Run `ruff check && ruff format`
2. Run `mypy gerdsenai_cli/`
3. Run tests: `pytest`
4. Update TODO.md if completing major tasks
5. Follow commit message format

### Before Every Release
1. Update version in `__init__.py`
2. Update CHANGELOG.md
3. Run full test suite
4. Performance regression testing
5. Security scan of dependencies

---

*These rules are living documents and should be updated as the project evolves. Always prioritize local LLM performance and user experience.*
