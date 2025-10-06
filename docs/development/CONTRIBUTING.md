# Contributing to GerdsenAI CLI

Thank you for your interest in contributing to GerdsenAI CLI! This guide will help you get started.

---

> **🚨 MANDATORY: Virtual Environment Usage**
> 
> **You MUST use the project's `.venv` virtual environment for ALL operations.**
> 
> ```bash
> # ALWAYS run this first
> source .venv/bin/activate
> 
> # Verify before proceeding
> echo $VIRTUAL_ENV  # Must show project path
> which python       # Must show .venv/bin/python
> ```
>
> **This is non-negotiable. All contributions must be developed in the venv.**

---

## 📋 Table of Contents

- [Code of Conduct](#-code-of-conduct)
- [Getting Started](#-getting-started)
- [Development Environment](#-development-environment)
- [Making Changes](#-making-changes)
- [Testing](#-testing)
- [Code Style](#-code-style)
- [Submitting Changes](#-submitting-changes)
- [Review Process](#-review-process)

## 🤝 Code of Conduct

- Be respectful and inclusive
- Provide constructive feedback
- Focus on code quality and maintainability
- Help others learn and grow

## 🚀 Getting Started

### 1. Fork and Clone

```bash
# Fork the repository on GitHub first, then:
git clone https://github.com/YOUR_USERNAME/GerdsenAI-CLI.git
cd GerdsenAI-CLI
```

### 2. Create Virtual Environment (First Time Only)

```bash
# ONLY if .venv doesn't exist yet
# Use Python 3.11+ (project uses 3.11.13)
python3 -m venv .venv

# Activate it
source .venv/bin/activate

# Verify Python version
python --version  # Should show Python 3.11+
```

### 3. Create a Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/your-bug-fix
```

## 🛠 Development Environment

### Required Tools

- **Python 3.11+** (inside .venv)
- **Git** for version control
- **VS Code** (recommended) or your preferred editor

### VS Code Setup

The project includes VS Code settings that automatically use `.venv`:

```json
// .vscode/settings.json (already configured)
{
  "python.defaultInterpreterPath": "${workspaceFolder}/.venv/bin/python",
  "python.terminal.activateEnvironment": true
}
```

**Verify VS Code is using correct Python:**
1. Open Command Palette (Cmd+Shift+P / Ctrl+Shift+P)
2. Type "Python: Select Interpreter"
3. Choose `.venv/bin/python`

### Daily Development Workflow

**Every single time you work on the project:**

```bash
# 1. Navigate to project
cd GerdsenAI-CLI

# 2. Activate venv (MANDATORY)
source .venv/bin/activate

# 3. Verify (paranoid but safe)
echo $VIRTUAL_ENV  # Check it's active

# 4. Pull latest changes
git pull origin main

# 5. Update dependencies if needed
pip install -e ".[dev]"

# 6. Now you can work
# ... make changes ...

# 7. Run tests before committing
pytest -v

# 8. Commit and push
git add .
git commit -m "feat: your changes"
git push origin your-branch
```

## 🔧 Making Changes

### Before You Start

1. **Check for existing issues** - avoid duplicate work
2. **Open an issue** for discussion (for major changes)
3. **Ensure venv is active** - `echo $VIRTUAL_ENV`
4. **Create a feature branch** - `git checkout -b feature/name`

### Code Guidelines

#### Python Style

```python
# Use type hints
def process_data(input: str, count: int) -> list[str]:
    """Process input data.
    
    Args:
        input: The input string to process
        count: Number of times to process
        
    Returns:
        List of processed strings
    """
    return [input] * count

# Use async/await for I/O
async def fetch_data() -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        return response.json()

# No emojis in code output (project rule)
console.print("[green]Success![/green]")  # ✅ Good
console.print("✅ Success!")  # ❌ Bad (emoji in output)
```

#### File Structure

```
gerdsenai_cli/
├── core/           # Core logic (agent, context, file operations)
├── commands/       # Command implementations
├── ui/             # User interface (TUI, animations)
├── config/         # Configuration management
└── utils/          # Utilities and helpers

tests/              # Mirror structure of main package
├── test_core/
├── test_commands/
└── conftest.py     # Shared fixtures
```

### Testing Your Changes

**⚠️ CRITICAL: Always activate venv before testing**

```bash
# Verify venv first
source .venv/bin/activate
echo $VIRTUAL_ENV  # Must show project path

# Run all tests
pytest -v

# Run specific test file
pytest tests/test_modes.py -v

# Run specific test
pytest tests/test_modes.py::TestExecutionMode::test_mode_values -v

# Run with coverage
pytest --cov=gerdsenai_cli --cov-report=html

# View coverage report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

### Adding Tests

**Every new feature MUST include tests.**

```python
# tests/test_your_feature.py
import pytest
from gerdsenai_cli.your_module import YourClass

class TestYourFeature:
    """Test suite for your feature."""
    
    def test_basic_functionality(self):
        """Test basic feature works."""
        instance = YourClass()
        result = instance.do_something()
        assert result == expected_value
    
    @pytest.mark.asyncio
    async def test_async_functionality(self):
        """Test async feature works."""
        instance = YourClass()
        result = await instance.do_async()
        assert result.success
```

## 🎨 Code Style

### Linting and Formatting

**Run before every commit:**

```bash
# Ensure venv is active
source .venv/bin/activate

# Check code with ruff
ruff check gerdsenai_cli/

# Format code with ruff
ruff format gerdsenai_cli/

# Type check with mypy
mypy gerdsenai_cli/
```

### Pre-commit Hooks (Optional but Recommended)

```bash
# Install pre-commit
pip install pre-commit

# Install hooks
pre-commit install

# Now checks run automatically on git commit
```

## 📤 Submitting Changes

### Commit Message Format

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `test`: Test additions/changes
- `refactor`: Code refactoring
- `style`: Formatting changes
- `chore`: Build/tooling changes

**Examples:**
```bash
git commit -m "feat(ui): add thinking mode toggle command"
git commit -m "fix(core): resolve capability detection for local models"
git commit -m "docs(readme): update venv setup instructions"
git commit -m "test(integration): add MCP server management tests"
```

### Pull Request Checklist

Before submitting a PR, ensure:

- [ ] **Venv was used** for all development and testing
- [ ] All tests pass: `pytest -v`
- [ ] Code is formatted: `ruff format gerdsenai_cli/`
- [ ] No linting errors: `ruff check gerdsenai_cli/`
- [ ] Type checking passes: `mypy gerdsenai_cli/`
- [ ] Documentation is updated (if needed)
- [ ] Commit messages follow format
- [ ] Branch is up to date with main
- [ ] PR description explains changes clearly

### Creating a Pull Request

1. **Push your branch:**
   ```bash
   git push origin feature/your-feature-name
   ```

2. **Go to GitHub** and create a Pull Request

3. **Fill in the PR template:**
   - **Title**: Clear, descriptive title
   - **Description**: What changed and why
   - **Testing**: How you tested the changes
   - **Screenshots**: If UI changes
   - **Breaking changes**: List any breaking changes

4. **Link related issues**: Reference issue numbers (#123)

## 🔍 Review Process

### What Reviewers Look For

1. **Code Quality**
   - Clear, readable code
   - Proper error handling
   - Type hints used
   - Documentation included

2. **Testing**
   - Tests included for new features
   - Tests actually test the feature
   - Edge cases covered
   - Tests pass consistently

3. **Virtual Environment**
   - All work done in `.venv`
   - No system Python references
   - Dependencies properly managed

4. **Style**
   - Follows project conventions
   - Ruff linting passes
   - No emojis in code output
   - Async/await for I/O

### Response Time

- Initial review: Within 2-3 days
- Follow-up reviews: Within 1-2 days
- Merge: After approval and CI passes

### Addressing Feedback

```bash
# Make requested changes
# ... edit files ...

# Commit changes
git add .
git commit -m "fix: address review feedback"

# Push to same branch
git push origin feature/your-feature-name
# PR automatically updates
```

## 🐛 Reporting Bugs

### Before Reporting

1. **Activate venv** and reproduce the bug
2. **Check existing issues** - may already be reported
3. **Test with latest version** - may already be fixed

### Bug Report Format

```markdown
**Description**
Clear description of the bug

**To Reproduce**
1. Activate venv: `source .venv/bin/activate`
2. Run command: `python -m gerdsenai_cli`
3. Do action X
4. See error

**Expected Behavior**
What should happen

**Actual Behavior**
What actually happens

**Environment**
- OS: macOS 14.0
- Python: 3.11.0 (from .venv)
- GerdsenAI CLI: 0.1.0
- Virtual env: ✅ Active

**Additional Context**
- Error logs
- Screenshots
- Related issues
```

## 💡 Feature Requests

### Suggesting Features

1. **Open an issue** with label `enhancement`
2. **Describe the use case** - why is this needed?
3. **Propose implementation** - how might it work?
4. **Consider alternatives** - other approaches?

### Implementation Process

1. Discussion and feedback
2. Design approval
3. Implementation in feature branch (in .venv!)
4. Tests and documentation
5. Code review
6. Merge to main

## 📚 Resources

- [Python Type Hints](https://docs.python.org/3/library/typing.html)
- [Asyncio Documentation](https://docs.python.org/3/library/asyncio.html)
- [Pytest Documentation](https://docs.pytest.org/)
- [Ruff Documentation](https://docs.astral.sh/ruff/)
- [Conventional Commits](https://www.conventionalcommits.org/)

## ❓ Questions?

- **General questions**: Open a [Discussion](https://github.com/GerdsenAI/GerdsenAI-CLI/discussions)
- **Bug reports**: Open an [Issue](https://github.com/GerdsenAI/GerdsenAI-CLI/issues)
- **Pull requests**: Tag @maintainers for review

## 🙏 Thank You!

Your contributions make this project better for everyone!

---

**Remember: ALWAYS use `.venv` - `source .venv/bin/activate` 🐍**
