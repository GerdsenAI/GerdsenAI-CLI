"""
Tests for conversation I/O utilities.
"""

from datetime import datetime

import pytest

from gerdsenai_cli.utils.conversation_io import (
    ConversationExporter,
    ConversationManager,
    ConversationSerializer,
)


class TestConversationSerializer:
    """Test conversation serialization."""

    def test_serialize_empty_conversation(self):
        """Test serializing empty conversation."""
        result = ConversationSerializer.serialize([])

        assert result["version"] == "1.0"
        assert "created_at" in result
        assert result["messages"] == []

    def test_serialize_with_messages(self):
        """Test serializing conversation with messages."""
        now = datetime.now()
        messages = [
            ("user", "Hello", now),
            ("assistant", "Hi there!", now),
        ]

        result = ConversationSerializer.serialize(messages)

        assert len(result["messages"]) == 2
        assert result["messages"][0]["role"] == "user"
        assert result["messages"][0]["content"] == "Hello"
        assert result["messages"][1]["role"] == "assistant"

    def test_serialize_with_metadata(self):
        """Test serializing with metadata."""
        messages = [("user", "Test", datetime.now())]
        metadata = {"model": "gpt-4", "tokens": 100}

        result = ConversationSerializer.serialize(messages, metadata)

        assert result["metadata"] == metadata

    def test_deserialize_valid_data(self):
        """Test deserializing valid conversation data."""
        now = datetime.now()
        data = {
            "version": "1.0",
            "messages": [
                {
                    "role": "user",
                    "content": "Hello",
                    "timestamp": now.isoformat(),
                },
            ],
        }

        messages = ConversationSerializer.deserialize(data)

        assert len(messages) == 1
        assert messages[0][0] == "user"
        assert messages[0][1] == "Hello"
        assert isinstance(messages[0][2], datetime)

    def test_deserialize_missing_messages(self):
        """Test deserializing data without messages key."""
        data = {"version": "1.0"}

        with pytest.raises(ValueError, match="missing 'messages' key"):
            ConversationSerializer.deserialize(data)

    def test_deserialize_invalid_message_format(self):
        """Test deserializing with invalid message format."""
        data = {
            "messages": [
                {"role": "user"}  # Missing content and timestamp
            ]
        }

        with pytest.raises(ValueError, match="missing required keys"):
            ConversationSerializer.deserialize(data)

    def test_roundtrip_serialization(self):
        """Test that serialize -> deserialize preserves data."""
        now = datetime.now()
        original_messages = [
            ("user", "First message", now),
            ("assistant", "Response", now),
            ("user", "Follow-up", now),
        ]

        # Serialize
        data = ConversationSerializer.serialize(original_messages)

        # Deserialize
        restored_messages = ConversationSerializer.deserialize(data)

        # Compare (timestamps may have microsecond differences due to ISO format)
        assert len(restored_messages) == len(original_messages)
        for orig, restored in zip(original_messages, restored_messages, strict=False):
            assert orig[0] == restored[0]  # role
            assert orig[1] == restored[1]  # content
            # Timestamps should be close (within 1 second)
            time_diff = abs((orig[2] - restored[2]).total_seconds())
            assert time_diff < 1.0

    def test_save_and_load_file(self, tmp_path):
        """Test saving and loading conversation files."""
        filepath = tmp_path / "test_conversation.json"
        now = datetime.now()
        messages = [
            ("user", "Test message", now),
            ("assistant", "Test response", now),
        ]
        metadata = {"model": "test-model"}

        # Save
        ConversationSerializer.save_to_file(filepath, messages, metadata)

        assert filepath.exists()

        # Load
        loaded_messages, loaded_metadata = ConversationSerializer.load_from_file(filepath)

        assert len(loaded_messages) == 2
        assert loaded_metadata == metadata

    def test_load_nonexistent_file(self, tmp_path):
        """Test loading non-existent file raises error."""
        filepath = tmp_path / "nonexistent.json"

        with pytest.raises(FileNotFoundError):
            ConversationSerializer.load_from_file(filepath)


class TestConversationExporter:
    """Test conversation export functionality."""

    def test_export_empty_conversation(self):
        """Test exporting empty conversation."""
        markdown = ConversationExporter.to_markdown([])

        assert "# GerdsenAI Conversation" in markdown
        assert "Exported:" in markdown

    def test_export_with_messages(self):
        """Test exporting conversation with messages."""
        now = datetime.now()
        messages = [
            ("user", "Hello, AI!", now),
            ("assistant", "Hello! How can I help?", now),
        ]

        markdown = ConversationExporter.to_markdown(messages)

        assert "## User" in markdown
        assert "## GerdsenAI" in markdown
        assert "Hello, AI!" in markdown
        assert "Hello! How can I help?" in markdown

    def test_export_with_metadata(self):
        """Test exporting with metadata."""
        messages = [("user", "Test", datetime.now())]
        metadata = {"model": "gpt-4", "tokens": 150}

        markdown = ConversationExporter.to_markdown(messages, metadata)

        assert "## Metadata" in markdown
        assert "model" in markdown
        assert "gpt-4" in markdown

    def test_export_command_messages(self):
        """Test exporting command messages with code blocks."""
        now = datetime.now()
        messages = [("command", "Help text here", now)]

        markdown = ConversationExporter.to_markdown(messages)

        assert "## Command" in markdown
        assert "```" in markdown
        assert "Help text here" in markdown

    def test_save_markdown_file(self, tmp_path):
        """Test saving markdown export to file."""
        filepath = tmp_path / "export.md"
        messages = [("user", "Test", datetime.now())]

        ConversationExporter.save_markdown(filepath, messages)

        assert filepath.exists()
        content = filepath.read_text()
        assert "# GerdsenAI Conversation" in content


class TestConversationManager:
    """Test high-level conversation manager."""

    def test_initialization(self, tmp_path):
        """Test manager initialization."""
        manager = ConversationManager(base_dir=tmp_path)

        assert manager.conversations_dir.exists()
        assert manager.exports_dir.exists()

    def test_list_empty_conversations(self, tmp_path):
        """Test listing when no conversations exist."""
        manager = ConversationManager(base_dir=tmp_path)

        conversations = manager.list_conversations()

        assert conversations == []

    def test_save_and_list_conversations(self, tmp_path):
        """Test saving and listing conversations."""
        manager = ConversationManager(base_dir=tmp_path)
        now = datetime.now()
        messages = [("user", "Test", now)]

        # Save conversation
        filepath = manager.save_conversation("test_conv", messages)

        assert filepath.exists()
        assert filepath.name == "test_conv.json"

        # List conversations
        conversations = manager.list_conversations()

        assert len(conversations) == 1
        assert conversations[0].stem == "test_conv"

    def test_save_with_extension(self, tmp_path):
        """Test saving handles .json extension automatically."""
        manager = ConversationManager(base_dir=tmp_path)
        messages = [("user", "Test", datetime.now())]

        # Save with explicit .json
        filepath1 = manager.save_conversation("test1.json", messages)
        # Save without extension
        filepath2 = manager.save_conversation("test2", messages)

        assert filepath1.name == "test1.json"
        assert filepath2.name == "test2.json"

    def test_load_conversation(self, tmp_path):
        """Test loading conversation."""
        manager = ConversationManager(base_dir=tmp_path)
        now = datetime.now()
        original_messages = [
            ("user", "Question", now),
            ("assistant", "Answer", now),
        ]
        metadata = {"model": "test"}

        # Save
        manager.save_conversation("test", original_messages, metadata)

        # Load
        loaded_messages, loaded_metadata = manager.load_conversation("test")

        assert len(loaded_messages) == 2
        assert loaded_metadata == metadata

    def test_load_with_extension(self, tmp_path):
        """Test loading handles .json extension automatically."""
        manager = ConversationManager(base_dir=tmp_path)
        messages = [("user", "Test", datetime.now())]

        manager.save_conversation("test", messages)

        # Load with and without extension
        loaded1, _ = manager.load_conversation("test")
        loaded2, _ = manager.load_conversation("test.json")

        assert len(loaded1) == len(loaded2) == 1

    def test_export_conversation_auto_filename(self, tmp_path):
        """Test exporting with auto-generated filename."""
        manager = ConversationManager(base_dir=tmp_path)
        messages = [("user", "Test", datetime.now())]

        filepath = manager.export_conversation(None, messages)

        assert filepath.exists()
        assert filepath.suffix == ".md"
        assert "conversation_" in filepath.name

    def test_export_conversation_custom_filename(self, tmp_path):
        """Test exporting with custom filename."""
        manager = ConversationManager(base_dir=tmp_path)
        messages = [("user", "Test", datetime.now())]

        filepath = manager.export_conversation("my_export", messages)

        assert filepath.exists()
        assert filepath.name == "my_export.md"

    def test_export_with_metadata(self, tmp_path):
        """Test exporting with metadata included."""
        manager = ConversationManager(base_dir=tmp_path)
        messages = [("user", "Test", datetime.now())]
        metadata = {"model": "gpt-4", "tokens": 200}

        filepath = manager.export_conversation("test", messages, metadata)

        content = filepath.read_text()
        assert "model" in content
        assert "gpt-4" in content
