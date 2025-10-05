"""
Conversation I/O utilities for saving, loading, and exporting conversations.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


class ConversationSerializer:
    """Handle conversation serialization to/from JSON."""
    
    @staticmethod
    def serialize(
        messages: list[tuple[str, str, datetime]],
        metadata: Optional[dict[str, Any]] = None
    ) -> dict[str, Any]:
        """Serialize conversation messages to a JSON-compatible dict.
        
        Args:
            messages: List of (role, content, timestamp) tuples
            metadata: Optional metadata (model, tokens, etc.)
            
        Returns:
            JSON-compatible dict with conversation data
        """
        serialized_messages = []
        for role, content, timestamp in messages:
            serialized_messages.append({
                "role": role,
                "content": content,
                "timestamp": timestamp.isoformat(),
            })
        
        result = {
            "version": "1.0",
            "created_at": datetime.now().isoformat(),
            "messages": serialized_messages,
        }
        
        if metadata:
            result["metadata"] = metadata
        
        return result
    
    @staticmethod
    def deserialize(data: dict[str, Any]) -> list[tuple[str, str, datetime]]:
        """Deserialize conversation from JSON-compatible dict.
        
        Args:
            data: JSON-compatible dict with conversation data
            
        Returns:
            List of (role, content, timestamp) tuples
            
        Raises:
            ValueError: If data format is invalid
        """
        if "messages" not in data:
            raise ValueError("Invalid conversation format: missing 'messages' key")
        
        messages = []
        for msg in data["messages"]:
            if not all(key in msg for key in ["role", "content", "timestamp"]):
                raise ValueError("Invalid message format: missing required keys")
            
            role = msg["role"]
            content = msg["content"]
            timestamp = datetime.fromisoformat(msg["timestamp"])
            
            messages.append((role, content, timestamp))
        
        return messages
    
    @staticmethod
    def save_to_file(
        filepath: Path,
        messages: list[tuple[str, str, datetime]],
        metadata: Optional[dict[str, Any]] = None
    ) -> None:
        """Save conversation to a JSON file.
        
        Args:
            filepath: Path to save the conversation
            messages: List of (role, content, timestamp) tuples
            metadata: Optional metadata
        """
        # Ensure parent directory exists
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        # Serialize and save
        data = ConversationSerializer.serialize(messages, metadata)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved conversation to {filepath}")
    
    @staticmethod
    def load_from_file(filepath: Path) -> tuple[list[tuple[str, str, datetime]], dict[str, Any]]:
        """Load conversation from a JSON file.
        
        Args:
            filepath: Path to the conversation file
            
        Returns:
            Tuple of (messages, metadata)
            
        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file format is invalid
        """
        if not filepath.exists():
            raise FileNotFoundError(f"Conversation file not found: {filepath}")
        
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        messages = ConversationSerializer.deserialize(data)
        metadata = data.get("metadata", {})
        
        logger.info(f"Loaded conversation from {filepath}")
        return messages, metadata


class ConversationExporter:
    """Export conversations to various formats."""
    
    @staticmethod
    def to_markdown(
        messages: list[tuple[str, str, datetime]],
        metadata: Optional[dict[str, Any]] = None
    ) -> str:
        """Export conversation to markdown format.
        
        Args:
            messages: List of (role, content, timestamp) tuples
            metadata: Optional metadata to include in header
            
        Returns:
            Markdown-formatted conversation
        """
        lines = []
        
        # Header with metadata
        lines.append("# GerdsenAI Conversation")
        lines.append("")
        
        if metadata:
            lines.append("## Metadata")
            lines.append("")
            for key, value in metadata.items():
                lines.append(f"- **{key}**: {value}")
            lines.append("")
        
        # Export timestamp
        lines.append(f"*Exported: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
        lines.append("")
        lines.append("---")
        lines.append("")
        
        # Messages
        for role, content, timestamp in messages:
            time_str = timestamp.strftime("%H:%M:%S")
            
            if role == "user":
                lines.append(f"## User ({time_str})")
                lines.append("")
                lines.append(content)
                lines.append("")
            elif role == "assistant":
                lines.append(f"## GerdsenAI ({time_str})")
                lines.append("")
                lines.append(content)
                lines.append("")
            elif role == "command":
                lines.append(f"## Command ({time_str})")
                lines.append("")
                lines.append("```")
                lines.append(content)
                lines.append("```")
                lines.append("")
        
        return "\n".join(lines)
    
    @staticmethod
    def save_markdown(
        filepath: Path,
        messages: list[tuple[str, str, datetime]],
        metadata: Optional[dict[str, Any]] = None
    ) -> None:
        """Save conversation as markdown file.
        
        Args:
            filepath: Path to save the markdown file
            messages: List of (role, content, timestamp) tuples
            metadata: Optional metadata
        """
        # Ensure parent directory exists
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        # Generate markdown
        markdown = ConversationExporter.to_markdown(messages, metadata)
        
        # Save to file
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(markdown)
        
        logger.info(f"Exported conversation to markdown: {filepath}")


class ConversationManager:
    """High-level manager for conversation I/O operations."""
    
    def __init__(self, base_dir: Optional[Path] = None):
        """Initialize conversation manager.
        
        Args:
            base_dir: Base directory for conversations (defaults to ~/.gerdsenai)
        """
        if base_dir is None:
            base_dir = Path.home() / ".gerdsenai"
        
        self.base_dir = base_dir
        self.conversations_dir = base_dir / "conversations"
        self.exports_dir = base_dir / "exports"
        
        # Create directories
        self.conversations_dir.mkdir(parents=True, exist_ok=True)
        self.exports_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"ConversationManager initialized with base_dir: {base_dir}")
    
    def list_conversations(self) -> list[Path]:
        """List all saved conversations.
        
        Returns:
            List of conversation file paths
        """
        return sorted(self.conversations_dir.glob("*.json"))
    
    def save_conversation(
        self,
        filename: str,
        messages: list[tuple[str, str, datetime]],
        metadata: Optional[dict[str, Any]] = None
    ) -> Path:
        """Save conversation with automatic filename handling.
        
        Args:
            filename: Desired filename (with or without .json extension)
            messages: List of (role, content, timestamp) tuples
            metadata: Optional metadata
            
        Returns:
            Path to the saved file
        """
        # Ensure .json extension
        if not filename.endswith('.json'):
            filename = f"{filename}.json"
        
        filepath = self.conversations_dir / filename
        ConversationSerializer.save_to_file(filepath, messages, metadata)
        return filepath
    
    def load_conversation(self, filename: str) -> tuple[list[tuple[str, str, datetime]], dict[str, Any]]:
        """Load conversation by filename.
        
        Args:
            filename: Conversation filename (with or without .json extension)
            
        Returns:
            Tuple of (messages, metadata)
        """
        # Ensure .json extension
        if not filename.endswith('.json'):
            filename = f"{filename}.json"
        
        filepath = self.conversations_dir / filename
        return ConversationSerializer.load_from_file(filepath)
    
    def export_conversation(
        self,
        filename: Optional[str],
        messages: list[tuple[str, str, datetime]],
        metadata: Optional[dict[str, Any]] = None
    ) -> Path:
        """Export conversation to markdown with automatic filename handling.
        
        Args:
            filename: Desired filename (None for auto-generated)
            messages: List of (role, content, timestamp) tuples
            metadata: Optional metadata
            
        Returns:
            Path to the exported file
        """
        # Auto-generate filename if not provided
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"conversation_{timestamp}.md"
        
        # Ensure .md extension
        if not filename.endswith('.md'):
            filename = f"{filename}.md"
        
        filepath = self.exports_dir / filename
        ConversationExporter.save_markdown(filepath, messages, metadata)
        return filepath
