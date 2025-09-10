# GerdsenAI CLI Development Rules

Based on the repository audit and TODO.md analysis, these rules ensure consistent development practices, package management, and local LLM optimization for the GerdsenAI CLI project.

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

## 📦 Package Management

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
Follow TODO.md phase structure:
1. **Phase 1**: Project scaffolding (✅ Complete)
2. **Phase 2**: Configuration and LLM client (✅ Complete)
3. **Phase 3**: Interactive loop and commands (🚧 In Progress)
4. **Phase 4**: Core agentic features (📅 Planned)
5. **Phase 5**: Advanced features (📅 Planned)
6. **Phase 6**: Testing and documentation (📅 Planned)

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