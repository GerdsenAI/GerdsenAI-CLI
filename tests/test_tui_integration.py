"""
Tests for TUI command integration with conversation I/O.

These tests verify that save/load/export commands work correctly
when called from the TUI with actual conversation data.
"""

from datetime import datetime
from unittest.mock import Mock

import pytest

from gerdsenai_cli.config.settings import Settings
from gerdsenai_cli.main import GerdsenAICLI
from gerdsenai_cli.utils.conversation_io import ConversationManager


class MockTUI:
    """Mock TUI for testing command integration."""

    def __init__(self):
        self.conversation = Mock()
        self.conversation.messages = []
        self.conversation.clear_messages = Mock()
        self.conversation.add_message = Mock()
        self.system_footer = ""

    def set_system_footer(self, text: str):
        """Mock system footer setter."""
        self.system_footer = text


@pytest.fixture
def cli_instance(tmp_path):
    """Create CLI instance with temporary conversation directory."""
    cli = GerdsenAICLI()

    # Override conversation manager to use temp directory
    cli.conversation_manager = ConversationManager(base_dir=tmp_path)

    # Create mock settings
    cli.settings = Settings()
    cli.settings.current_model = "test-model"

    return cli


@pytest.fixture
def mock_tui():
    """Create mock TUI with sample conversation."""
    tui = MockTUI()

    # Add sample messages
    tui.conversation.messages = [
        ("user", "Hello, how are you?", datetime(2025, 1, 1, 12, 0, 0)),
        ("assistant", "I'm doing well, thank you!", datetime(2025, 1, 1, 12, 0, 1)),
        ("user", "What's 2+2?", datetime(2025, 1, 1, 12, 0, 2)),
        ("assistant", "2+2 equals 4.", datetime(2025, 1, 1, 12, 0, 3)),
    ]

    return tui


@pytest.mark.asyncio
async def test_save_command_with_tui(cli_instance, mock_tui):
    """Test /save command saves conversation from TUI."""
    response = await cli_instance._handle_tui_command("/save", ["test_chat"], tui=mock_tui)

    assert "saved successfully" in response.lower()
    assert "test_chat" in response
    assert "Messages: 4" in response

    # Verify file exists
    saved_files = list(cli_instance.conversation_manager.conversations_dir.glob("test_chat.json"))
    assert len(saved_files) == 1


@pytest.mark.asyncio
async def test_save_command_without_tui(cli_instance):
    """Test /save command fails gracefully without TUI."""
    response = await cli_instance._handle_tui_command("/save", ["test_chat"], tui=None)

    assert "error" in response.lower()
    assert "tui not available" in response.lower()


@pytest.mark.asyncio
async def test_save_command_empty_conversation(cli_instance):
    """Test /save command handles empty conversation."""
    empty_tui = MockTUI()
    empty_tui.conversation.messages = []

    response = await cli_instance._handle_tui_command("/save", ["test_chat"], tui=empty_tui)

    assert "no messages" in response.lower()


@pytest.mark.asyncio
async def test_save_command_no_filename(cli_instance, mock_tui):
    """Test /save command requires filename."""
    response = await cli_instance._handle_tui_command("/save", [], tui=mock_tui)

    assert "usage" in response.lower()
    assert "/save <filename>" in response.lower()


@pytest.mark.asyncio
async def test_load_command_lists_conversations(cli_instance, mock_tui, tmp_path):
    """Test /load command lists saved conversations."""
    # Save some conversations first
    await cli_instance._handle_tui_command("/save", ["chat1"], tui=mock_tui)
    await cli_instance._handle_tui_command("/save", ["chat2"], tui=mock_tui)

    # List conversations
    response = await cli_instance._handle_tui_command("/load", [], tui=mock_tui)

    assert "available conversations" in response.lower()
    assert "chat1" in response
    assert "chat2" in response
    assert "/load <filename>" in response


@pytest.mark.asyncio
async def test_load_command_loads_conversation(cli_instance, mock_tui):
    """Test /load command loads conversation into TUI."""
    # Save a conversation first
    await cli_instance._handle_tui_command("/save", ["test_load"], tui=mock_tui)

    # Create new TUI with empty conversation
    new_tui = MockTUI()

    # Load conversation
    response = await cli_instance._handle_tui_command("/load", ["test_load"], tui=new_tui)

    assert "loaded successfully" in response.lower()
    assert "test_load" in response
    assert "Messages: 4" in response

    # Verify clear was called
    new_tui.conversation.clear_messages.assert_called_once()

    # Verify messages were added (4 messages)
    assert new_tui.conversation.add_message.call_count == 4


@pytest.mark.asyncio
async def test_load_command_not_found(cli_instance, mock_tui):
    """Test /load command handles missing conversation."""
    response = await cli_instance._handle_tui_command("/load", ["nonexistent"], tui=mock_tui)

    assert "not found" in response.lower()
    assert "nonexistent" in response


@pytest.mark.asyncio
async def test_load_command_without_tui(cli_instance):
    """Test /load command for listing works without TUI."""
    # List should work without TUI
    response = await cli_instance._handle_tui_command("/load", [], tui=None)

    assert "no saved conversations" in response.lower() or "available conversations" in response.lower()


@pytest.mark.asyncio
async def test_export_command_with_tui(cli_instance, mock_tui):
    """Test /export command exports conversation from TUI."""
    response = await cli_instance._handle_tui_command("/export", ["test_export"], tui=mock_tui)

    assert "exported successfully" in response.lower()
    assert "test_export" in response
    assert "markdown" in response.lower()
    assert "Messages: 4" in response

    # Verify file exists
    exported_files = list(cli_instance.conversation_manager.exports_dir.glob("test_export.md"))
    assert len(exported_files) == 1


@pytest.mark.asyncio
async def test_export_command_auto_filename(cli_instance, mock_tui):
    """Test /export command with auto-generated filename."""
    response = await cli_instance._handle_tui_command("/export", [], tui=mock_tui)

    assert "exported successfully" in response.lower()
    assert "markdown" in response.lower()
    assert "Messages: 4" in response

    # Verify a file was created
    exported_files = list(cli_instance.conversation_manager.exports_dir.glob("*.md"))
    assert len(exported_files) >= 1


@pytest.mark.asyncio
async def test_export_command_without_tui(cli_instance):
    """Test /export command fails gracefully without TUI."""
    response = await cli_instance._handle_tui_command("/export", ["test"], tui=None)

    assert "error" in response.lower()
    assert "tui not available" in response.lower()


@pytest.mark.asyncio
async def test_export_command_empty_conversation(cli_instance):
    """Test /export command handles empty conversation."""
    empty_tui = MockTUI()
    empty_tui.conversation.messages = []

    response = await cli_instance._handle_tui_command("/export", ["test"], tui=empty_tui)

    assert "no messages" in response.lower()


@pytest.mark.asyncio
async def test_model_command_updates_footer(cli_instance, mock_tui):
    """Test /model command updates TUI footer."""
    response = await cli_instance._handle_tui_command("/model", ["new-model"], tui=mock_tui)

    assert "switched to model" in response.lower()
    assert "new-model" in response

    # Verify footer was updated
    assert mock_tui.system_footer == "Model: new-model"


@pytest.mark.asyncio
async def test_model_command_without_args(cli_instance, mock_tui):
    """Test /model command shows current model."""
    response = await cli_instance._handle_tui_command("/model", [], tui=mock_tui)

    assert "current model" in response.lower()
    assert "test-model" in response


@pytest.mark.asyncio
async def test_roundtrip_save_load(cli_instance, mock_tui):
    """Test saving and loading preserves conversation."""
    # Save conversation
    save_response = await cli_instance._handle_tui_command("/save", ["roundtrip"], tui=mock_tui)
    assert "saved successfully" in save_response.lower()

    # Create new TUI
    new_tui = MockTUI()

    # Load conversation
    load_response = await cli_instance._handle_tui_command("/load", ["roundtrip"], tui=new_tui)
    assert "loaded successfully" in load_response.lower()

    # Verify all messages were added
    assert new_tui.conversation.add_message.call_count == len(mock_tui.conversation.messages)


@pytest.mark.asyncio
async def test_save_with_metadata(cli_instance, mock_tui):
    """Test save command includes metadata."""
    # Save conversation
    await cli_instance._handle_tui_command("/save", ["with_metadata"], tui=mock_tui)

    # Load and check metadata
    _, metadata = cli_instance.conversation_manager.load_conversation("with_metadata")

    assert "model" in metadata
    assert metadata["model"] == "test-model"
    assert "message_count" in metadata
    assert metadata["message_count"] == 4


@pytest.mark.asyncio
async def test_export_includes_metadata(cli_instance, mock_tui, tmp_path):
    """Test export includes metadata in markdown."""
    # Export conversation
    await cli_instance._handle_tui_command("/export", ["with_meta"], tui=mock_tui)

    # Read exported file
    export_file = cli_instance.conversation_manager.exports_dir / "with_meta.md"
    content = export_file.read_text()

    # Verify metadata is present (markdown format uses **key**: value)
    assert "**model**: test-model" in content
    assert "**message_count**: 4" in content


@pytest.mark.asyncio
async def test_unknown_command(cli_instance, mock_tui):
    """Test unknown command returns error message."""
    response = await cli_instance._handle_tui_command("/unknown", [], tui=mock_tui)

    assert "unknown command" in response.lower()
    assert "/unknown" in response
