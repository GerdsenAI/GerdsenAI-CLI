#!/bin/bash
set -euo pipefail

echo "🚀 Setting up GerdsenAI-CLI development environment..."

# Ensure we're in the workspace directory
cd /workspace

# Install the project in editable mode (no virtual environment needed in container)
echo "📦 Installing GerdsenAI-CLI in editable mode..."
pip install -e .

# Install additional development dependencies
echo "🔧 Installing development dependencies..."
pip install \
    pytest-cov \
    pre-commit \
    sphinx \
    sphinx-rtd-theme

# Validate the installation
echo "✅ Validating installation..."
if python -c "import gerdsenai_cli; print(f'✅ GerdsenAI-CLI {gerdsenai_cli.__version__} imported successfully')"; then
    echo "✅ Package import successful"
else
    echo "❌ Package import failed"
    exit 1
fi

# Test CLI entry point
if python -m gerdsenai_cli --version >/dev/null 2>&1; then
    echo "✅ CLI entry point working"
else
    echo "❌ CLI entry point failed"
    exit 1
fi

# Set up git configuration if not already set (for CI/CD)
if [ -z "$(git config --global user.name || true)" ]; then
    git config --global user.name "GerdsenAI-CLI Developer"
    git config --global user.email "dev@gerdsenai.com"
    echo "📝 Set default git configuration"
fi

# Set up pre-commit hooks
if [ -f .pre-commit-config.yaml ]; then
    echo "🪝 Installing pre-commit hooks..."
    pre-commit install
fi

# Create development shortcuts
echo "⚡ Creating development shortcuts..."
cat > /home/python/.zshrc_gerdsenai << 'EOF'
# GerdsenAI-CLI Development Shortcuts
alias gcli='python -m gerdsenai_cli'
alias gtest='pytest -v'
alias glint='ruff check gerdsenai_cli/ && mypy gerdsenai_cli/'
alias gformat='ruff format gerdsenai_cli/ && black gerdsenai_cli/'
alias gbuild='python -m build'

# Show security status
alias gsec='echo "🔒 Security Level: $SECURITY_LEVEL" && ipset list allowed-domains | wc -l | xargs echo "🌐 Allowed domains:"'

echo "🛡️  GerdsenAI-CLI Development Container Ready!"
echo "🔒 Security Level: $SECURITY_LEVEL"
echo "📋 Available shortcuts: gcli, gtest, glint, gformat, gbuild, gsec"
EOF

# Source the shortcuts in zsh
echo "source /home/python/.zshrc_gerdsenai" >> /home/python/.zshrc

# Set permissions
chown python:python /home/python/.zshrc_gerdsenai

echo "✨ Post-create setup complete!"
echo ""
echo "🎯 Quick Start:"
echo "  • Run the CLI: gcli"
echo "  • Run tests: gtest"  
echo "  • Format code: gformat"
echo "  • Check security: gsec"
echo ""
echo "🔐 Your development environment is secure and ready for AI-assisted development!"
