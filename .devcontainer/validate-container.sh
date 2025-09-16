#!/bin/bash
set -euo pipefail

echo "🔍 Validating GerdsenAI-CLI Container Environment..."

# Check Python version
echo "📋 Checking Python version..."
python_version=$(python --version)
echo "✅ $python_version"

# Check if we're in container
if [ "${DEVCONTAINER:-}" = "true" ]; then
    echo "✅ Running in DevContainer environment"
else
    echo "⚠️  Not running in DevContainer environment"
fi

# Check security level
echo "🔒 Security Level: ${SECURITY_LEVEL:-strict}"

# Validate core packages
echo "📦 Validating core packages..."
packages=("typer" "rich" "httpx" "pydantic" "ruff" "black" "mypy" "pytest")
for pkg in "${packages[@]}"; do
    if python -c "import $pkg" 2>/dev/null; then
        echo "✅ $pkg installed"
    else
        echo "❌ $pkg missing"
        exit 1
    fi
done

# Check GerdsenAI-CLI installation
echo "🚀 Checking GerdsenAI-CLI installation..."
if python -c "import gerdsenai_cli; print(f'Version: {gerdsenai_cli.__version__}')" 2>/dev/null; then
    echo "✅ GerdsenAI-CLI imported successfully"
else
    echo "❌ GerdsenAI-CLI import failed"
    exit 1
fi

# Test CLI entry point
echo "🎯 Testing CLI entry point..."
if python -m gerdsenai_cli --version >/dev/null 2>&1; then
    echo "✅ CLI entry point working"
else
    echo "❌ CLI entry point failed"
    exit 1
fi

# Check development shortcuts
echo "⚡ Checking development shortcuts..."
shortcuts=("gcli" "gtest" "glint" "gformat" "gbuild" "gsec")
for shortcut in "${shortcuts[@]}"; do
    if command -v $shortcut >/dev/null 2>&1; then
        echo "✅ $shortcut available"
    else
        echo "ℹ️  $shortcut not yet available (run 'source ~/.zshrc' or restart shell)"
    fi
done

# Security validation (if firewall is active)
if command -v iptables >/dev/null 2>&1 && [ "$(id -u)" -eq 0 ]; then
    echo "🛡️  Testing firewall (requires root)..."
    if curl --connect-timeout 3 https://example.com >/dev/null 2>&1; then
        echo "⚠️  Firewall may not be active - unauthorized access allowed"
    else
        echo "✅ Firewall blocking unauthorized access"
    fi
    
    if curl --connect-timeout 3 https://pypi.org >/dev/null 2>&1; then
        echo "✅ Firewall allowing authorized access (PyPI)"
    else
        echo "⚠️  Firewall may be blocking authorized access"
    fi
else
    echo "ℹ️  Firewall validation skipped (requires root)"
fi

echo ""
echo "🎉 Container validation complete!"
echo "🔐 Your secure AI development environment is ready!"
echo ""
echo "🎯 Next steps:"
echo "  • Run 'gcli' to start the CLI"
echo "  • Run 'gtest' to run tests"
echo "  • Run 'gsec' to check security status"
echo "  • Start coding with AI assistance!"
