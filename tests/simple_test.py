#!/usr/bin/env python3
"""
Simple validation for Phase 7 changes
"""

print("🧪 Testing GerdsenAI CLI Phase 7 Implementation...")

# Test 1: Check if renamed command files exist with proper structure
print("\n1. Checking command file structure...")

try:
    # Check agent.py for renamed commands
    with open(
        "/Users/gerdsenai/Documents/GerdsenAI-CLI/gerdsenai_cli/commands/agent.py"
    ) as f:
        content = f.read()

    if "class ChatCommand" in content:
        print("✅ ChatCommand class found in agent.py")
    else:
        print("❌ ChatCommand class NOT found in agent.py")

    if "class ResetCommand" in content:
        print("✅ ResetCommand class found in agent.py")
    else:
        print("❌ ResetCommand class NOT found in agent.py")

    # Check files.py for renamed commands
    with open(
        "/Users/gerdsenai/Documents/GerdsenAI-CLI/gerdsenai_cli/commands/files.py"
    ) as f:
        content = f.read()

    if "class FilesCommand" in content:
        print("✅ FilesCommand class found in files.py")
    else:
        print("❌ FilesCommand class NOT found in files.py")

    if "class ReadCommand" in content:
        print("✅ ReadCommand class found in files.py")
    else:
        print("❌ ReadCommand class NOT found in files.py")

    # Check system.py for new ToolsCommand
    with open(
        "/Users/gerdsenai/Documents/GerdsenAI-CLI/gerdsenai_cli/commands/system.py"
    ) as f:
        content = f.read()

    if "class ToolsCommand" in content:
        print("✅ ToolsCommand class found in system.py")
    else:
        print("❌ ToolsCommand class NOT found in system.py")

except Exception as e:
    print(f"❌ Error checking command files: {e}")

# Test 2: Check main.py integration
print("\n2. Checking main.py integration...")

try:
    with open("/Users/gerdsenai/Documents/GerdsenAI-CLI/gerdsenai_cli/main.py") as f:
        content = f.read()

    expected_imports = [
        "ChatCommand",
        "ResetCommand",
        "FilesCommand",
        "ReadCommand",
        "ToolsCommand",
    ]

    for import_name in expected_imports:
        if import_name in content:
            print(f"✅ {import_name} imported in main.py")
        else:
            print(f"❌ {import_name} NOT imported in main.py")

    expected_registrations = [
        "ChatCommand(**command_deps)",
        "ResetCommand(**command_deps)",
        "FilesCommand(**command_deps)",
        "ReadCommand(**command_deps)",
        "ToolsCommand(**command_deps)",
    ]

    for reg in expected_registrations:
        if reg in content:
            print(f"✅ {reg} registered in main.py")
        else:
            print(f"❌ {reg} NOT registered in main.py")

except Exception as e:
    print(f"❌ Error checking main.py: {e}")

# Test 3: Check project structure
print("\n3. Checking project structure integrity...")

import os

key_files = [
    "/Users/gerdsenai/Documents/GerdsenAI-CLI/gerdsenai_cli/__init__.py",
    "/Users/gerdsenai/Documents/GerdsenAI-CLI/gerdsenai_cli/cli.py",
    "/Users/gerdsenai/Documents/GerdsenAI-CLI/gerdsenai_cli/main.py",
    "/Users/gerdsenai/Documents/GerdsenAI-CLI/gerdsenai-ascii-art.txt",
    "/Users/gerdsenai/Documents/GerdsenAI-CLI/pyproject.toml",
    "/Users/gerdsenai/Documents/GerdsenAI-CLI/TODO.md",
]

for file_path in key_files:
    if os.path.exists(file_path):
        print(f"✅ {os.path.basename(file_path)} exists")
    else:
        print(f"❌ {os.path.basename(file_path)} missing")

print("\n4. Summary...")
print("🎉 Phase 7 file structure validation complete!")
print("📝 Key changes implemented:")
print("   • ConversationCommand → ChatCommand")
print("   • ClearSessionCommand → ResetCommand")
print("   • ListFilesCommand → FilesCommand")
print("   • ReadFileCommand → ReadCommand")
print("   • Added ToolsCommand")
print("   • Updated main.py integrations")

print("\n🧪 To test the CLI interactively:")
print("   cd /Users/gerdsenai/Documents/GerdsenAI-CLI")
print("   source .venv/bin/activate")
print("   python -m gerdsenai_cli")

print("\n📋 Test the new commands:")
print("   /tools                    # New command")
print("   /chat show               # Renamed from /conversation")
print("   /reset                   # Renamed from /clear")
print("   /files                   # Renamed from /ls")
print("   /read somefile.py        # Renamed from /cat")
print("   /conversation show       # Backward compatibility alias")
print("   /clear                   # Backward compatibility alias")
print("   /ls                      # Backward compatibility alias")
print("   /cat somefile.py         # Backward compatibility alias")
