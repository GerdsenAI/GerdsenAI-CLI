"""Unit tests for CommandParser class."""
from gerdsenai_cli.ui.prompt_toolkit_tui import CommandParser


class TestCommandParser:
    """Test suite for CommandParser."""

    def test_is_command_with_slash(self):
        """Test that strings starting with / are recognized as commands."""
        assert CommandParser.is_command("/help")
        assert CommandParser.is_command("/clear")
        assert CommandParser.is_command("/model gpt-4")
        assert CommandParser.is_command("  /help  ")  # With whitespace

    def test_is_command_without_slash(self):
        """Test that strings not starting with / are not commands."""
        assert not CommandParser.is_command("help")
        assert not CommandParser.is_command("Hello world")
        assert not CommandParser.is_command("What is /help?")
        assert not CommandParser.is_command("")

    def test_parse_command_no_args(self):
        """Test parsing commands without arguments."""
        command, args = CommandParser.parse("/help")
        assert command == "/help"
        assert args == []

        command, args = CommandParser.parse("/clear")
        assert command == "/clear"
        assert args == []

    def test_parse_command_with_args(self):
        """Test parsing commands with arguments."""
        command, args = CommandParser.parse("/model gpt-4")
        assert command == "/model"
        assert args == ["gpt-4"]

        command, args = CommandParser.parse("/save my_conversation")
        assert command == "/save"
        assert args == ["my_conversation"]

        command, args = CommandParser.parse("/model gpt-4 turbo")
        assert command == "/model"
        assert args == ["gpt-4", "turbo"]

    def test_parse_empty_string(self):
        """Test parsing empty string."""
        command, args = CommandParser.parse("")
        assert command == ""
        assert args == []

    def test_parse_with_extra_whitespace(self):
        """Test parsing with extra whitespace."""
        command, args = CommandParser.parse("  /help  ")
        assert command == "/help"
        assert args == []

        command, args = CommandParser.parse("  /model   gpt-4   ")
        assert command == "/model"
        assert args == ["gpt-4"]

    def test_get_help_text_format(self):
        """Test that help text is properly formatted."""
        help_text = CommandParser.get_help_text()

        assert "Available Commands:" in help_text
        assert "/help" in help_text
        assert "/clear" in help_text
        assert "/model" in help_text
        assert "/debug" in help_text
        assert "/save" in help_text
        assert "/load" in help_text
        assert "/export" in help_text
        assert "/shortcuts" in help_text
        assert "/exit" in help_text
        assert "/quit" in help_text

    def test_get_help_text_has_descriptions(self):
        """Test that help text includes descriptions."""
        help_text = CommandParser.get_help_text()

        # Check that descriptions are present
        assert "Show available commands" in help_text
        assert "Clear conversation history" in help_text
        assert "Show or switch AI model" in help_text
        assert "Toggle debug mode" in help_text

    def test_get_shortcuts_text_format(self):
        """Test that shortcuts text is properly formatted."""
        shortcuts_text = CommandParser.get_shortcuts_text()

        assert "Keyboard Shortcuts:" in shortcuts_text
        assert "Message Input:" in shortcuts_text
        assert "Navigation:" in shortcuts_text
        assert "Text Selection" in shortcuts_text  # May include "& Copy" in section header
        assert "General:" in shortcuts_text

    def test_get_shortcuts_text_has_shortcuts(self):
        """Test that shortcuts text includes key shortcuts."""
        shortcuts_text = CommandParser.get_shortcuts_text()

        assert "Enter" in shortcuts_text
        assert "Shift+Enter" in shortcuts_text
        assert "Page Up" in shortcuts_text
        assert "Page Down" in shortcuts_text
        assert "Ctrl+S" in shortcuts_text
        assert "Ctrl+C" in shortcuts_text
        assert "Escape" in shortcuts_text

    def test_commands_dict_completeness(self):
        """Test that COMMANDS dict has all expected commands."""
        commands = CommandParser.COMMANDS

        assert "/help" in commands
        assert "/clear" in commands
        assert "/model" in commands
        assert "/debug" in commands
        assert "/save" in commands
        assert "/load" in commands
        assert "/export" in commands
        assert "/shortcuts" in commands
        assert "/exit" in commands
        assert "/quit" in commands

    def test_case_sensitivity(self):
        """Test command case sensitivity."""
        # Commands should be case-sensitive
        assert CommandParser.is_command("/HELP")
        assert CommandParser.is_command("/Help")

        command, _ = CommandParser.parse("/HELP")
        assert command == "/HELP"  # Preserve case

    def test_special_characters_in_args(self):
        """Test parsing commands with special characters in arguments."""
        command, args = CommandParser.parse("/save my-conversation_2024.json")
        assert command == "/save"
        assert args == ["my-conversation_2024.json"]

        command, args = CommandParser.parse("/export my_file.md")
        assert command == "/export"
        assert args == ["my_file.md"]
