"""
Persistent context memory system for GerdsenAI CLI.

Tracks discussed files, topics, and user preferences across sessions
to provide intelligent context recall and continuity.
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class FileReference:
    """Reference to a file discussed in conversation."""

    path: str
    first_mentioned: str  # ISO timestamp
    last_mentioned: str  # ISO timestamp
    mention_count: int = 1
    topics: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "path": self.path,
            "first_mentioned": self.first_mentioned,
            "last_mentioned": self.last_mentioned,
            "mention_count": self.mention_count,
            "topics": self.topics,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FileReference":
        """Create from dictionary."""
        return cls(
            path=data["path"],
            first_mentioned=data["first_mentioned"],
            last_mentioned=data["last_mentioned"],
            mention_count=data.get("mention_count", 1),
            topics=data.get("topics", []),
        )


@dataclass
class TopicReference:
    """Reference to a topic discussed in conversation."""

    name: str
    first_mentioned: str  # ISO timestamp
    last_mentioned: str  # ISO timestamp
    mention_count: int = 1
    related_files: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "first_mentioned": self.first_mentioned,
            "last_mentioned": self.last_mentioned,
            "mention_count": self.mention_count,
            "related_files": self.related_files,
            "keywords": self.keywords,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TopicReference":
        """Create from dictionary."""
        return cls(
            name=data["name"],
            first_mentioned=data["first_mentioned"],
            last_mentioned=data["last_mentioned"],
            mention_count=data.get("mention_count", 1),
            related_files=data.get("related_files", []),
            keywords=data.get("keywords", []),
        )


@dataclass
class ConversationEntry:
    """Entry in conversation history."""

    timestamp: str  # ISO timestamp
    role: str  # "user" or "assistant"
    content: str
    files_mentioned: list[str] = field(default_factory=list)
    topics: list[str] = field(default_factory=list)
    action_type: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp,
            "role": self.role,
            "content": self.content[:500],  # Truncate long content
            "files_mentioned": self.files_mentioned,
            "topics": self.topics,
            "action_type": self.action_type,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ConversationEntry":
        """Create from dictionary."""
        return cls(
            timestamp=data["timestamp"],
            role=data["role"],
            content=data["content"],
            files_mentioned=data.get("files_mentioned", []),
            topics=data.get("topics", []),
            action_type=data.get("action_type"),
        )


@dataclass
class UserPreference:
    """User preference or learned pattern."""

    key: str
    value: Any
    learned_from: (
        str  # How was this learned (e.g., "explicit", "inferred", "correction")
    )
    confidence: float  # 0.0 to 1.0
    timestamp: str  # ISO timestamp

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "key": self.key,
            "value": self.value,
            "learned_from": self.learned_from,
            "confidence": self.confidence,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "UserPreference":
        """Create from dictionary."""
        return cls(
            key=data["key"],
            value=data["value"],
            learned_from=data.get("learned_from", "explicit"),
            confidence=data.get("confidence", 1.0),
            timestamp=data.get("timestamp", datetime.now().isoformat()),
        )


class ProjectMemory:
    """Manages persistent project memory across sessions."""

    def __init__(self, project_root: Path | None = None):
        """Initialize project memory.

        Args:
            project_root: Root directory of the project
        """
        self.project_root = project_root or Path.cwd()
        self.memory_dir = self.project_root / ".gerdsenai"
        self.memory_file = self.memory_dir / "memory.json"

        # Memory storage
        self.files: dict[str, FileReference] = {}
        self.topics: dict[str, TopicReference] = {}
        self.preferences: dict[str, UserPreference] = {}
        self.conversation_history: list[ConversationEntry] = []
        self.metadata: dict[str, Any] = {
            "project_type": None,
            "created_at": None,
            "last_updated": None,
            "session_count": 0,
            "total_conversations": 0,
        }

        # Load existing memory
        self.load()

    def load(self) -> bool:
        """Load memory from disk.

        Returns:
            True if loaded successfully
        """
        if not self.memory_file.exists():
            logger.info("No existing memory file found")
            return False

        try:
            with open(self.memory_file) as f:
                data = json.load(f)

            # Load files
            self.files = {
                path: FileReference.from_dict(ref_data)
                for path, ref_data in data.get("files", {}).items()
            }

            # Load topics
            self.topics = {
                name: TopicReference.from_dict(topic_data)
                for name, topic_data in data.get("topics", {}).items()
            }

            # Load preferences
            self.preferences = {
                key: UserPreference.from_dict(pref_data)
                for key, pref_data in data.get("preferences", {}).items()
            }

            # Load conversation history
            self.conversation_history = [
                ConversationEntry.from_dict(entry_data)
                for entry_data in data.get("conversation_history", [])
            ]

            # Load metadata
            self.metadata = data.get("metadata", self.metadata)

            logger.info(
                f"Loaded memory: {len(self.files)} files, {len(self.topics)} topics, "
                f"{len(self.conversation_history)} conversations"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to load memory: {e}")
            return False

    def save(self) -> bool:
        """Save memory to disk.

        Returns:
            True if saved successfully
        """
        try:
            # Ensure directory exists
            self.memory_dir.mkdir(parents=True, exist_ok=True)

            # Update metadata
            self.metadata["last_updated"] = datetime.now().isoformat()
            if self.metadata.get("created_at") is None:
                self.metadata["created_at"] = self.metadata["last_updated"]
            self.metadata["session_count"] = self.metadata.get("session_count", 0) + 1

            # Prepare data
            data = {
                "files": {path: ref.to_dict() for path, ref in self.files.items()},
                "topics": {
                    name: topic.to_dict() for name, topic in self.topics.items()
                },
                "preferences": {
                    key: pref.to_dict() for key, pref in self.preferences.items()
                },
                "conversation_history": [
                    entry.to_dict()
                    for entry in self.conversation_history[
                        -100:
                    ]  # Keep last 100 entries
                ],
                "metadata": self.metadata,
            }

            # Write to file
            with open(self.memory_file, "w") as f:
                json.dump(data, f, indent=2)

            logger.info(
                f"Saved memory: {len(self.files)} files, {len(self.topics)} topics, "
                f"{len(self.conversation_history)} conversations"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to save memory: {e}")
            return False

    def remember_file(self, file_path: str, topic: str | None = None) -> None:
        """Remember a file that was discussed.

        Args:
            file_path: Path to the file
            topic: Optional topic associated with the file
        """
        now = datetime.now().isoformat()

        if file_path in self.files:
            # Update existing reference
            ref = self.files[file_path]
            ref.last_mentioned = now
            ref.mention_count += 1
            if topic and topic not in ref.topics:
                ref.topics.append(topic)
        else:
            # Create new reference
            self.files[file_path] = FileReference(
                path=file_path,
                first_mentioned=now,
                last_mentioned=now,
                mention_count=1,
                topics=[topic] if topic else [],
            )

        logger.debug(f"Remembered file: {file_path}")

    def remember_topic(
        self,
        topic: str,
        related_file: str | None = None,
        keywords: list[str] | None = None,
    ) -> None:
        """Remember a topic that was discussed.

        Args:
            topic: Topic name
            related_file: Optional file related to the topic
            keywords: Optional keywords associated with the topic
        """
        now = datetime.now().isoformat()

        if topic in self.topics:
            # Update existing reference
            ref = self.topics[topic]
            ref.last_mentioned = now
            ref.mention_count += 1
            if related_file and related_file not in ref.related_files:
                ref.related_files.append(related_file)
            if keywords:
                ref.keywords.extend([kw for kw in keywords if kw not in ref.keywords])
        else:
            # Create new reference
            self.topics[topic] = TopicReference(
                name=topic,
                first_mentioned=now,
                last_mentioned=now,
                mention_count=1,
                related_files=[related_file] if related_file else [],
                keywords=keywords or [],
            )

        logger.debug(f"Remembered topic: {topic}")

    def remember_preference(
        self,
        key: str,
        value: Any,
        learned_from: str = "explicit",
        confidence: float = 1.0,
    ) -> None:
        """Remember a user preference.

        Args:
            key: Preference key
            value: Preference value
            learned_from: How was this learned
            confidence: Confidence level (0.0 to 1.0)
        """
        self.preferences[key] = UserPreference(
            key=key,
            value=value,
            learned_from=learned_from,
            confidence=confidence,
            timestamp=datetime.now().isoformat(),
        )

        logger.debug(f"Remembered preference: {key} = {value}")

    def recall_file(self, file_path: str) -> FileReference | None:
        """Recall information about a file.

        Args:
            file_path: Path to the file

        Returns:
            FileReference or None if not found
        """
        return self.files.get(file_path)

    def recall_topic(self, topic: str) -> TopicReference | None:
        """Recall information about a topic.

        Args:
            topic: Topic name

        Returns:
            TopicReference or None if not found
        """
        return self.topics.get(topic)

    def recall_preference(self, key: str) -> Any | None:
        """Recall a user preference.

        Args:
            key: Preference key

        Returns:
            Preference value or None if not found
        """
        pref = self.preferences.get(key)
        return pref.value if pref else None

    def get_recent_files(self, limit: int = 10) -> list[FileReference]:
        """Get recently mentioned files.

        Args:
            limit: Maximum number of files to return

        Returns:
            List of FileReference objects sorted by recency
        """
        sorted_files = sorted(
            self.files.values(), key=lambda f: f.last_mentioned, reverse=True
        )
        return sorted_files[:limit]

    def get_frequent_files(self, limit: int = 10) -> list[FileReference]:
        """Get frequently mentioned files.

        Args:
            limit: Maximum number of files to return

        Returns:
            List of FileReference objects sorted by mention count
        """
        sorted_files = sorted(
            self.files.values(), key=lambda f: f.mention_count, reverse=True
        )
        return sorted_files[:limit]

    def get_files_by_topic(self, topic: str) -> list[str]:
        """Get files associated with a topic.

        Args:
            topic: Topic name

        Returns:
            List of file paths
        """
        # Direct topic lookup
        if topic in self.topics:
            return self.topics[topic].related_files.copy()

        # Search files that mention this topic
        result = []
        for file_path, ref in self.files.items():
            if topic.lower() in [t.lower() for t in ref.topics]:
                result.append(file_path)

        return result

    def forget_file(self, file_path: str) -> bool:
        """Forget a file from memory.

        Args:
            file_path: Path to the file

        Returns:
            True if file was forgotten
        """
        if file_path in self.files:
            del self.files[file_path]
            logger.info(f"Forgot file: {file_path}")
            return True
        return False

    def forget_topic(self, topic: str) -> bool:
        """Forget a topic from memory.

        Args:
            topic: Topic name

        Returns:
            True if topic was forgotten
        """
        if topic in self.topics:
            del self.topics[topic]
            logger.info(f"Forgot topic: {topic}")
            return True
        return False

    def remember_conversation(
        self,
        role: str,
        content: str,
        files_mentioned: list[str] | None = None,
        topics: list[str] | None = None,
        action_type: str | None = None,
    ) -> None:
        """Remember a conversation entry.

        Args:
            role: "user" or "assistant"
            content: Conversation content
            files_mentioned: Files mentioned in conversation
            topics: Topics discussed
            action_type: Type of action if any
        """
        entry = ConversationEntry(
            timestamp=datetime.now().isoformat(),
            role=role,
            content=content,
            files_mentioned=files_mentioned or [],
            topics=topics or [],
            action_type=action_type,
        )

        self.conversation_history.append(entry)
        self.metadata["total_conversations"] = (
            self.metadata.get("total_conversations", 0) + 1
        )

        # Auto-track files and topics
        for file_path in files_mentioned or []:
            self.remember_file(file_path, topics[0] if topics else None)

        for topic in topics or []:
            self.remember_topic(topic)

        logger.debug(
            f"Remembered {role} conversation with {len(files_mentioned or [])} files"
        )

    def get_recent_conversations(self, limit: int = 10) -> list[ConversationEntry]:
        """Get recent conversation entries.

        Args:
            limit: Maximum number of entries to return

        Returns:
            List of ConversationEntry objects
        """
        return self.conversation_history[-limit:]

    def extract_topics_from_text(self, text: str) -> list[str]:
        """Extract potential topics from text using simple keyword extraction.

        Args:
            text: Text to analyze

        Returns:
            List of extracted topics
        """
        # Common technical topics and keywords
        topic_keywords = [
            "testing",
            "deployment",
            "security",
            "authentication",
            "authorization",
            "api",
            "database",
            "frontend",
            "backend",
            "ui",
            "ux",
            "performance",
            "optimization",
            "refactoring",
            "bug",
            "error",
            "configuration",
            "documentation",
            "logging",
            "monitoring",
            "caching",
            "architecture",
        ]

        text_lower = text.lower()
        found_topics = []

        for keyword in topic_keywords:
            if keyword in text_lower:
                found_topics.append(keyword)

        return found_topics[:5]  # Limit to 5 topics

    def get_context_summary(self) -> str:
        """Get a summary of relevant context for LLM.

        Returns:
            Formatted context summary
        """
        recent_files = self.get_recent_files(5)
        self.get_frequent_files(5)

        summary = ""

        if recent_files:
            summary += "Recently discussed files:\n"
            for ref in recent_files:
                summary += f"- {ref.path} ({ref.mention_count} times)\n"

        if self.topics:
            summary += "\nRecent topics:\n"
            sorted_topics = sorted(
                self.topics.values(), key=lambda t: t.last_mentioned, reverse=True
            )[:5]
            for topic in sorted_topics:
                summary += f"- {topic.name}\n"

        return summary

    def clear(self) -> None:
        """Clear all memory."""
        self.files.clear()
        self.topics.clear()
        self.preferences.clear()
        self.conversation_history.clear()
        self.metadata = {
            "project_type": None,
            "created_at": None,
            "last_updated": None,
            "session_count": 0,
            "total_conversations": 0,
        }
        logger.info("Cleared all memory")

    def get_summary(self) -> str:
        """Get a summary of stored memory.

        Returns:
            Formatted summary string
        """
        recent_files = self.get_recent_files(5)

        summary = "Project Memory Summary:\n\n"
        summary += f"Files tracked: {len(self.files)}\n"
        summary += f"Topics tracked: {len(self.topics)}\n"
        summary += f"Preferences: {len(self.preferences)}\n"
        summary += f"Conversations: {len(self.conversation_history)}\n"
        summary += f"Sessions: {self.metadata.get('session_count', 0)}\n"

        if recent_files:
            summary += "\nRecent files:\n"
            for ref in recent_files:
                summary += f"  • {ref.path} ({ref.mention_count} mentions)\n"

        if self.topics:
            summary += "\nTopics:\n"
            for topic_name in list(self.topics.keys())[:5]:
                topic = self.topics[topic_name]
                summary += f"  • {topic_name} ({topic.mention_count} mentions)\n"

        return summary
