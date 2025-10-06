#!/usr/bin/env python3
"""
Verify that the correct virtual environment is active.

This script checks that:
1. A virtual environment is active
2. It's the project's .venv directory
3. Python version is correct
4. Required packages are installed

Usage:
    python scripts/check_venv.py
    
Exit codes:
    0 - Virtual environment is correct
    1 - Not in virtual environment
    2 - Wrong virtual environment
    3 - Wrong Python version
    4 - Missing dependencies
"""

import sys
import os
from pathlib import Path


def main() -> int:
    """Check virtual environment status."""
    project_root = Path(__file__).parent.parent.resolve()
    expected_venv = project_root / ".venv"
    
    print("🔍 Checking Virtual Environment Setup...")
    print()
    
    # Check 1: Is a venv active?
    venv_path = os.environ.get("VIRTUAL_ENV")
    if not venv_path:
        print("❌ ERROR: No virtual environment is active!")
        print()
        print("To fix:")
        print(f"  source {expected_venv}/bin/activate")
        print()
        return 1
    
    venv_path = Path(venv_path).resolve()
    print(f"✓ Virtual environment active: {venv_path}")
    
    # Check 2: Is it the correct venv?
    if venv_path != expected_venv:
        print(f"⚠️  WARNING: Using wrong virtual environment!")
        print(f"   Expected: {expected_venv}")
        print(f"   Actual:   {venv_path}")
        print()
        print("To fix:")
        print("  deactivate  # Exit current venv")
        print(f"  source {expected_venv}/bin/activate")
        print()
        return 2
    
    print(f"✓ Using correct venv: .venv")
    
    # Check 3: Python version
    version = sys.version_info
    if version.major != 3 or version.minor < 11:
        print(f"❌ ERROR: Wrong Python version!")
        print(f"   Expected: Python 3.11+")
        print(f"   Actual:   Python {version.major}.{version.minor}.{version.micro}")
        print()
        print("To fix:")
        print("  Recreate venv with Python 3.11+")
        print(f"  python3.11 -m venv {expected_venv}")
        print(f"  source {expected_venv}/bin/activate")
        print(f"  pip install -e \".[dev]\"")
        print()
        return 3
    
    print(f"✓ Python version: {version.major}.{version.minor}.{version.micro}")
    
    # Check 4: Required packages
    missing_packages = []
    required_packages = [
        "pytest",
        "ruff",
        "mypy",
        "httpx",
        "rich",
        "typer",
        "prompt_toolkit",
    ]
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"❌ ERROR: Missing required packages:")
        for pkg in missing_packages:
            print(f"   - {pkg}")
        print()
        print("To fix:")
        print(f"  pip install -e \".[dev]\"")
        print()
        return 4
    
    print(f"✓ All required packages installed")
    
    # Check 5: Editable install
    try:
        import gerdsenai_cli
        package_location = Path(gerdsenai_cli.__file__).parent.parent
        if package_location.resolve() != project_root:
            print(f"⚠️  WARNING: Package not installed in editable mode")
            print(f"   Package location: {package_location}")
            print(f"   Project root:     {project_root}")
            print()
            print("To fix:")
            print(f"  pip install -e \".[dev]\"")
            print()
    except ImportError:
        print(f"⚠️  WARNING: gerdsenai_cli not installed")
        print()
        print("To fix:")
        print(f"  pip install -e \".[dev]\"")
        print()
    else:
        print(f"✓ Package installed in editable mode")
    
    # Success!
    print()
    print("=" * 60)
    print("✅ VIRTUAL ENVIRONMENT OK!")
    print("=" * 60)
    print()
    print("You can safely proceed with development:")
    print("  • Run tests: pytest -v")
    print("  • Run CLI: python -m gerdsenai_cli")
    print("  • Format code: ruff format gerdsenai_cli/")
    print("  • Check types: mypy gerdsenai_cli/")
    print()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
