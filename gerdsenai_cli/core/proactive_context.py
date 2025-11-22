"""
Proactive Context Builder for Smart File Reading.

This module automatically reads mentioned files and related dependencies
to build comprehensive context without requiring explicit /read commands.
"""

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class ContextPriority:
    """Priority levels for context inclusion."""

    CRITICAL = 10  # Explicitly mentioned files
    HIGH = 8  # Direct imports/dependencies
    MEDIUM = 5  # Related files (same directory)
    LOW = 3  # Transitive dependencies
    BACKGROUND = 1  # General project context


@dataclass
class FileReadResult:
    """Result of reading a file for context."""

    file_path: Path
    content: str
    priority: int
    token_estimate: int
    read_reason: str  # Why this file was read
    truncated: bool = False


class ProactiveContextBuilder:
    """
    Automatically builds context by reading mentioned files and dependencies.

    This eliminates the need for explicit /read commands - when a user mentions
    a file, the system automatically reads it and related files.
    """

    # File patterns for different programming languages
    IMPORT_PATTERNS = {
        "python": [
            r"^from\s+([\w.]+)\s+import",  # from x import y
            r"^import\s+([\w.]+)",  # import x
        ],
        "javascript": [
            r"import\s+.*\s+from\s+['\"]([^'\"]+)['\"]",  # ES6 imports
            r"require\(['\"]([^'\"]+)['\"]\)",  # CommonJS require
        ],
        "typescript": [
            r"import\s+.*\s+from\s+['\"]([^'\"]+)['\"]",
            r"import\s+['\"]([^'\"]+)['\"]",  # Side-effect imports
        ],
    }

    def __init__(
        self,
        project_root: Path,
        max_context_tokens: int = 100000,
        context_usage_ratio: float = 0.7,
    ):
        """
        Initialize proactive context builder.

        Args:
            project_root: Root directory of the project
            max_context_tokens: Maximum tokens to include in context
            context_usage_ratio: Ratio of max tokens to actually use (reserve for response)
        """
        self.project_root = project_root
        self.max_context_tokens = max_context_tokens
        self.context_budget = int(max_context_tokens * context_usage_ratio)

        self.file_cache: dict[Path, str] = {}  # Cache file contents
        self.read_files: set[Path] = set()  # Track what we've read

        logger.info(
            f"ProactiveContextBuilder initialized with {self.context_budget:,} token budget"
        )

    def extract_file_mentions(self, text: str) -> list[tuple[str, int]]:
        """
        Extract file mentions from user input.

        Args:
            text: Text to analyze (user input or conversation)

        Returns:
            List of (file_path, confidence) tuples
        """
        mentions = []

        # Pattern 1: Explicit file paths with extensions
        explicit_pattern = r"[\w/.-]+\.(?:py|js|ts|tsx|jsx|java|cpp|h|hpp|c|rs|go|rb|php|md|txt|json|yaml|yml|toml|sh|bash)"
        explicit_matches = re.findall(explicit_pattern, text, re.IGNORECASE)

        for match in explicit_matches:
            # Clean up the path
            path = match.strip(".,;:!?()[]{}\"'")
            mentions.append((path, 10))  # High confidence - explicit path

        # Pattern 2: Code entity mentions (e.g., "Agent class", "FileEditor")
        # These might refer to files even without extension
        entity_pattern = r"\b([A-Z][a-zA-Z0-9_]+(?:Manager|Service|Handler|Client|Editor|Parser|Builder))\b"
        entity_matches = re.findall(entity_pattern, text)

        for match in entity_matches:
            # Convert PascalCase to snake_case for Python
            snake_case = re.sub(r"(?<!^)(?=[A-Z])", "_", match).lower()
            mentions.append((f"{snake_case}.py", 5))  # Medium confidence - inferred

        # Pattern 3: Directory mentions
        dir_pattern = r"\b((?:[\w-]+/)+[\w-]+)\b"
        dir_matches = re.findall(dir_pattern, text)

        for match in dir_matches:
            if "/" in match and not match.startswith("http"):
                mentions.append((match, 3))  # Lower confidence - might be directory

        return mentions

    async def build_smart_context(
        self,
        user_query: str,
        conversation_history: Optional[list[str]] = None,
        explicitly_mentioned: Optional[list[str]] = None,
    ) -> dict[str, FileReadResult]:
        """
        Build context by reading mentioned files and their dependencies.

        Args:
            user_query: Current user query
            conversation_history: Recent conversation for context
            explicitly_mentioned: Files explicitly requested (highest priority)

        Returns:
            Dictionary of file_path -> FileReadResult
        """
        context_files: dict[str, FileReadResult] = {}
        current_tokens = 0

        # Priority 1: Explicitly mentioned files (CRITICAL)
        if explicitly_mentioned:
            for file_str in explicitly_mentioned:
                file_path = self._resolve_file_path(file_str)
                if file_path:
                    result = await self._read_file_with_priority(
                        file_path,
                        ContextPriority.CRITICAL,
                        "Explicitly requested by user",
                    )
                    if result:
                        context_files[str(file_path)] = result
                        current_tokens += result.token_estimate

        # Priority 2: Files mentioned in current query (HIGH)
        query_mentions = self.extract_file_mentions(user_query)
        for file_str, confidence in sorted(
            query_mentions, key=lambda x: x[1], reverse=True
        ):
            if current_tokens >= self.context_budget:
                logger.info("Context budget exhausted, stopping file reads")
                break

            file_path = self._resolve_file_path(file_str)
            if file_path and str(file_path) not in context_files:
                result = await self._read_file_with_priority(
                    file_path,
                    ContextPriority.HIGH,
                    f"Mentioned in query (confidence: {confidence})",
                )
                if result:
                    context_files[str(file_path)] = result
                    current_tokens += result.token_estimate

        # Priority 3: Related files (imports, dependencies) (MEDIUM)
        # For each file we've read, find its dependencies
        for file_key in list(context_files.keys()):
            if current_tokens >= self.context_budget:
                break

            file_path = Path(file_key)
            related_files = await self._find_related_files(file_path)

            for related_path in related_files:
                if current_tokens >= self.context_budget:
                    break

                if str(related_path) not in context_files:
                    result = await self._read_file_with_priority(
                        related_path,
                        ContextPriority.MEDIUM,
                        f"Related to {file_path.name}",
                    )
                    if result:
                        context_files[str(related_path)] = result
                        current_tokens += result.token_estimate

        # Priority 4: Files from conversation history (LOW)
        if conversation_history:
            history_text = " ".join(conversation_history[-5:])  # Last 5 messages
            history_mentions = self.extract_file_mentions(history_text)

            for file_str, _ in history_mentions:
                if current_tokens >= self.context_budget:
                    break

                file_path = self._resolve_file_path(file_str)
                if file_path and str(file_path) not in context_files:
                    result = await self._read_file_with_priority(
                        file_path,
                        ContextPriority.LOW,
                        "Mentioned in recent conversation",
                    )
                    if result:
                        context_files[str(file_path)] = result
                        current_tokens += result.token_estimate

        logger.info(
            f"Built context with {len(context_files)} files, {current_tokens:,} estimated tokens"
        )
        return context_files

    async def _read_file_with_priority(
        self, file_path: Path, priority: int, reason: str
    ) -> Optional[FileReadResult]:
        """
        Read a file with given priority.

        Args:
            file_path: Path to file
            priority: Priority level (higher = more important)
            reason: Reason for reading this file

        Returns:
            FileReadResult or None if read failed
        """
        try:
            # Check if file exists
            if not file_path.exists():
                logger.warning(f"File not found: {file_path}")
                return None

            # Check if already in cache
            if file_path in self.file_cache:
                content = self.file_cache[file_path]
            else:
                # Read file
                content = file_path.read_text(encoding="utf-8", errors="ignore")
                self.file_cache[file_path] = content

            # Estimate tokens (rough: ~4 characters per token)
            token_estimate = len(content) // 4

            # Check if we need to truncate
            truncated = False
            if (
                token_estimate > self.context_budget * 0.3
            ):  # Single file shouldn't be >30%
                # Truncate: Keep beginning and end
                truncate_to = int(self.context_budget * 0.3 * 4)  # chars
                half = truncate_to // 2

                content = (
                    content[:half]
                    + f"\n\n... [Truncated {len(content) - truncate_to} characters] ...\n\n"
                    + content[-half:]
                )
                token_estimate = len(content) // 4
                truncated = True

            self.read_files.add(file_path)

            return FileReadResult(
                file_path=file_path,
                content=content,
                priority=priority,
                token_estimate=token_estimate,
                read_reason=reason,
                truncated=truncated,
            )

        except Exception as e:
            logger.error(f"Failed to read {file_path}: {e}")
            return None

    async def _find_related_files(self, file_path: Path) -> list[Path]:
        """
        Find files related to the given file (imports, tests, etc.).

        Args:
            file_path: Path to analyze

        Returns:
            List of related file paths
        """
        related = []

        try:
            # Get file content
            if file_path in self.file_cache:
                content = self.file_cache[file_path]
            else:
                content = file_path.read_text(encoding="utf-8", errors="ignore")

            # Detect language
            lang = self._detect_language(file_path)

            # Extract imports based on language
            if lang in self.IMPORT_PATTERNS:
                for pattern in self.IMPORT_PATTERNS[lang]:
                    imports = re.findall(pattern, content, re.MULTILINE)

                    for imp in imports:
                        # Convert import to file path
                        import_path = self._import_to_path(imp, file_path, lang)
                        if import_path and import_path.exists():
                            related.append(import_path)

            # Look for corresponding test file
            test_file = self._find_test_file(file_path)
            if test_file and test_file.exists():
                related.append(test_file)

        except Exception as e:
            logger.debug(f"Error finding related files for {file_path}: {e}")

        return related

    def _detect_language(self, file_path: Path) -> str:
        """Detect programming language from file extension."""
        ext_map = {
            ".py": "python",
            ".js": "javascript",
            ".jsx": "javascript",
            ".ts": "typescript",
            ".tsx": "typescript",
        }
        return ext_map.get(file_path.suffix.lower(), "unknown")

    def _import_to_path(
        self, import_str: str, source_file: Path, lang: str
    ) -> Optional[Path]:
        """Convert an import string to a file path."""
        if lang == "python":
            # Convert module path to file path (e.g., "foo.bar" -> "foo/bar.py")
            rel_path = import_str.replace(".", "/") + ".py"
            return self.project_root / rel_path
        elif lang in ["javascript", "typescript"]:
            # Relative import
            if import_str.startswith("."):
                return (source_file.parent / import_str).resolve()
            # Absolute import from project root
            else:
                return self.project_root / import_str

        return None

    def _find_test_file(self, file_path: Path) -> Optional[Path]:
        """Find corresponding test file for given source file."""
        # Pattern: source.py -> test_source.py or source_test.py
        name = file_path.stem

        test_patterns = [
            file_path.parent / f"test_{name}{file_path.suffix}",
            file_path.parent / f"{name}_test{file_path.suffix}",
            self.project_root / "tests" / f"test_{name}{file_path.suffix}",
            self.project_root / "test" / f"test_{name}{file_path.suffix}",
        ]

        for test_path in test_patterns:
            if test_path.exists():
                return test_path

        return None

    def _resolve_file_path(self, file_str: str) -> Optional[Path]:
        """
        Resolve a file string to an absolute Path.

        Args:
            file_str: File path string (relative or absolute)

        Returns:
            Resolved Path or None
        """
        # Try as-is first
        path = Path(file_str)

        if path.is_absolute() and path.exists():
            return path

        # Try relative to project root
        abs_path = (self.project_root / file_str).resolve()
        if abs_path.exists():
            return abs_path

        # Try removing leading slash
        if file_str.startswith("/"):
            abs_path = (self.project_root / file_str[1:]).resolve()
            if abs_path.exists():
                return abs_path

        logger.debug(f"Could not resolve file path: {file_str}")
        return None

    def clear_cache(self) -> None:
        """Clear file cache and read history."""
        self.file_cache.clear()
        self.read_files.clear()
        logger.info("ProactiveContextBuilder cache cleared")
