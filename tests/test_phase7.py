#!/usr/bin/env python3
"""
Test script for Phase 7 implementation - Command System Consistency
"""

import asyncio
import sys
from pathlib import Path

# Add the project to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


async def test_command_imports():
    """Test that all renamed commands can be imported successfully."""
    print("🧪 Testing Phase 7 Command Imports...")

    try:
        # Test renamed agent commands
        from gerdsenai_cli.commands.agent import ChatCommand, ResetCommand

        print("✅ Agent commands: ChatCommand, ResetCommand")

        # Test renamed file commands
        from gerdsenai_cli.commands.files import FilesCommand, ReadCommand

        print("✅ File commands: FilesCommand, ReadCommand")

        # Test new tools command
        from gerdsenai_cli.commands.system import ToolsCommand

        print("✅ System commands: ToolsCommand")

        return True

    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False


async def test_command_properties():
    """Test that command properties are correctly set."""
    print("\n🧪 Testing Command Properties...")

    try:
        from gerdsenai_cli.commands.agent import ChatCommand, ResetCommand
        from gerdsenai_cli.commands.files import FilesCommand, ReadCommand
        from gerdsenai_cli.commands.system import ToolsCommand

        # Test ChatCommand
        chat_cmd = ChatCommand()
        assert chat_cmd.name == "chat", f"Expected 'chat', got '{chat_cmd.name}'"
        assert "conversation" in chat_cmd.aliases, "Missing 'conversation' alias"
        print("✅ ChatCommand: name='chat', has 'conversation' alias")

        # Test ResetCommand
        reset_cmd = ResetCommand()
        assert reset_cmd.name == "reset", f"Expected 'reset', got '{reset_cmd.name}'"
        assert "clear" in reset_cmd.aliases, "Missing 'clear' alias"
        print("✅ ResetCommand: name='reset', has 'clear' alias")

        # Test FilesCommand
        files_cmd = FilesCommand()
        assert files_cmd.name == "files", f"Expected 'files', got '{files_cmd.name}'"
        assert "ls" in files_cmd.aliases, "Missing 'ls' alias"
        print("✅ FilesCommand: name='files', has 'ls' alias")

        # Test ReadCommand
        read_cmd = ReadCommand()
        assert read_cmd.name == "read", f"Expected 'read', got '{read_cmd.name}'"
        assert "cat" in read_cmd.aliases, "Missing 'cat' alias"
        print("✅ ReadCommand: name='read', has 'cat' alias")

        # Test ToolsCommand
        tools_cmd = ToolsCommand()
        assert tools_cmd.name == "tools", f"Expected 'tools', got '{tools_cmd.name}'"
        assert "capabilities" in tools_cmd.aliases, "Missing 'capabilities' alias"
        print("✅ ToolsCommand: name='tools', has 'capabilities' alias")

        return True

    except Exception as e:
        print(f"❌ Property test failed: {e}")
        return False


async def test_main_integration():
    """Test that main.py can import all the renamed commands."""
    print("\n🧪 Testing Main Integration...")

    try:
        # Test imports from main.py work
        from gerdsenai_cli.main import GerdsenAICLI

        print("✅ Main application imports successfully")

        # Create instance (won't initialize fully due to missing LLM server)
        app = GerdsenAICLI(debug=True)
        print("✅ GerdsenAICLI can be instantiated")

        return True

    except Exception as e:
        print(f"❌ Main integration test failed: {e}")
        return False


async def test_ascii_art():
    """Test that the ASCII art display works."""
    print("\n🧪 Testing ASCII Art Display...")

    try:
        from gerdsenai_cli.utils.display import get_ascii_art_path, show_ascii_art

        # Check ASCII art file exists
        art_path = get_ascii_art_path()
        if art_path.exists():
            print(f"✅ ASCII art file found: {art_path}")

            # Test display function (won't actually show in this context)
            show_ascii_art()  # This should not raise an exception
            print("✅ ASCII art display function works")
        else:
            print(f"❌ ASCII art file not found: {art_path}")
            return False

        return True

    except Exception as e:
        print(f"❌ ASCII art test failed: {e}")
        return False


async def main():
    """Run all tests."""
    print("🚀 GerdsenAI CLI - Phase 7 Testing\n")

    tests = [
        test_command_imports,
        test_command_properties,
        test_main_integration,
        test_ascii_art,
    ]

    results = []
    for test in tests:
        try:
            result = await test()
            results.append(result)
        except Exception as e:
            print(f"❌ Test {test.__name__} crashed: {e}")
            results.append(False)

    # Summary
    passed = sum(results)
    total = len(results)

    print(f"\n📊 Test Results: {passed}/{total} passed")

    if passed == total:
        print(
            "🎉 All Phase 7 tests PASSED! Command system consistency implemented successfully."
        )
        return 0
    else:
        print("⚠️  Some tests failed. Please check the implementation.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
