"""
Context Manager for GerdsenAI CLI.

This module handles project structure analysis, file filtering, and context building
for providing relevant information to the LLM about the current codebase.
"""

import asyncio
import fnmatch
import hashlib
import logging
import mimetypes
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.tree import Tree

from ..utils.display import show_error

logger = logging.getLogger(__name__)
console = Console()


@dataclass
class FileInfo:
    """Information about a file in the project."""

    path: Path
    relative_path: Path
    size: int
    modified_time: datetime
    mime_type: str | None
    is_text: bool
    is_binary: bool
    encoding: str | None = None
    content_hash: str | None = None
    cached_content: str | None = None

    def __post_init__(self):
        """Initialize computed properties."""
        if self.mime_type is None:
            self.mime_type, _ = mimetypes.guess_type(str(self.path))

        # Determine if file is text or binary
        if self.mime_type:
            self.is_text = self.mime_type.startswith("text/") or self.mime_type in [
                "application/json",
                "application/xml",
                "application/javascript",
                "application/x-yaml",
                "application/yaml",
            ]
            self.is_binary = not self.is_text
        else:
            # Fallback: check extension
            text_extensions = {
                ".txt",
                ".md",
                ".py",
                ".js",
                ".ts",
                ".jsx",
                ".tsx",
                ".html",
                ".css",
                ".scss",
                ".sass",
                ".less",
                ".json",
                ".yaml",
                ".yml",
                ".xml",
                ".svg",
                ".sql",
                ".sh",
                ".bash",
                ".zsh",
                ".fish",
                ".ps1",
                ".bat",
                ".cmd",
                ".dockerfile",
                ".gitignore",
                ".gitattributes",
                ".editorconfig",
                ".env",
                ".ini",
                ".cfg",
                ".conf",
                ".toml",
                ".lock",
                ".log",
            }
            self.is_text = self.path.suffix.lower() in text_extensions
            self.is_binary = not self.is_text


@dataclass
class ProjectStats:
    """Statistics about the analyzed project."""

    total_files: int = 0
    text_files: int = 0
    binary_files: int = 0
    ignored_files: int = 0
    total_size: int = 0
    languages: dict[str, int] = field(default_factory=dict)
    largest_files: list[tuple[Path, int]] = field(default_factory=list)


class GitignoreParser:
    """Parser for .gitignore files with proper pattern matching."""

    def __init__(self, gitignore_path: Path | None = None):
        """Initialize with optional gitignore file path."""
        self.patterns: list[tuple[str, bool]] = []  # (pattern, is_negation)
        self.base_path: Path | None = None

        if gitignore_path and gitignore_path.exists():
            self.load_gitignore(gitignore_path)

    def load_gitignore(self, gitignore_path: Path) -> None:
        """Load patterns from a .gitignore file."""
        try:
            self.base_path = gitignore_path.parent

            with open(gitignore_path, encoding="utf-8", errors="ignore") as f:
                for _line_num, line in enumerate(f, 1):
                    line = line.strip()

                    # Skip empty lines and comments
                    if not line or line.startswith("#"):
                        continue

                    # Check for negation
                    is_negation = line.startswith("!")
                    if is_negation:
                        line = line[1:]

                    # Normalize pattern
                    pattern = self._normalize_pattern(line)
                    self.patterns.append((pattern, is_negation))

        except Exception as e:
            logger.warning(f"Failed to load .gitignore from {gitignore_path}: {e}")

    def _normalize_pattern(self, pattern: str) -> str:
        """Normalize a gitignore pattern."""
        # Remove trailing whitespace
        pattern = pattern.rstrip()

        # Handle directory patterns
        if pattern.endswith("/"):
            pattern = pattern[:-1]

        return pattern

    def is_ignored(self, file_path: Path, is_directory: bool = False) -> bool:
        """Check if a file path matches any ignore patterns."""
        if not self.patterns or not self.base_path:
            return False

        try:
            # Get relative path from base
            rel_path = file_path.relative_to(self.base_path)
            path_str = str(rel_path)

            # Check against patterns (last match wins)
            is_ignored = False

            for pattern, is_negation in self.patterns:
                if self._matches_pattern(path_str, pattern, is_directory):
                    is_ignored = not is_negation

            return is_ignored

        except (ValueError, OSError):
            # Path is not relative to base
            return False

    def _matches_pattern(self, path: str, pattern: str, is_directory: bool) -> bool:
        """Check if a path matches a specific pattern."""
        # Handle absolute patterns (starting with /)
        if pattern.startswith("/"):
            pattern = pattern[1:]
            # Must match from root
            return fnmatch.fnmatch(path, pattern)

        # Handle directory-only patterns
        if pattern.endswith("/"):
            pattern = pattern[:-1]
            if not is_directory:
                return False

        # Check if pattern matches any part of the path
        path_parts = path.split("/")

        # Try matching the full path
        if fnmatch.fnmatch(path, pattern):
            return True

        # Try matching any suffix of the path
        for i in range(len(path_parts)):
            suffix = "/".join(path_parts[i:])
            if fnmatch.fnmatch(suffix, pattern):
                return True

        # Try matching just the filename
        if fnmatch.fnmatch(path_parts[-1], pattern):
            return True

        return False


class ProjectContext:
    """Manages project context and file analysis."""

    def __init__(
        self, project_root: Path | None = None, max_file_size: int = 1024 * 1024
    ):
        """
        Initialize the project context manager.

        Args:
            project_root: Root directory of the project (defaults to current directory)
            max_file_size: Maximum file size to read content (1MB default)
        """
        self.project_root = Path(project_root or os.getcwd()).resolve()
        self.max_file_size = max_file_size

        # File tracking
        self.files: dict[Path, FileInfo] = {}
        self.stats = ProjectStats()

        # Filtering
        self.gitignore = GitignoreParser()
        self.default_ignore_patterns = {
            # Version control
            ".git",
            ".svn",
            ".hg",
            ".bzr",
            # Dependencies
            "node_modules",
            "venv",
            "env",
            ".env",
            "__pycache__",
            ".pytest_cache",
            "vendor",
            ".composer",
            ".npm",
            ".yarn",
            # Build outputs
            "dist",
            "build",
            "target",
            "out",
            ".next",
            ".nuxt",
            # IDE files
            ".vscode",
            ".idea",
            "*.swp",
            "*.swo",
            ".DS_Store",
            "Thumbs.db",
            # Logs and temp
            "*.log",
            "*.tmp",
            "*.temp",
            ".cache",
            ".temp",
            # Binaries and media
            "*.exe",
            "*.dll",
            "*.so",
            "*.dylib",
            "*.app",
            "*.jpg",
            "*.jpeg",
            "*.png",
            "*.gif",
            "*.bmp",
            "*.ico",
            "*.mp3",
            "*.mp4",
            "*.avi",
            "*.mov",
            "*.wmv",
            "*.zip",
            "*.tar",
            "*.gz",
            "*.rar",
            "*.7z",
            # Database
            "*.db",
            "*.sqlite",
            "*.sqlite3",
        }

        # Content cache
        self.content_cache: dict[str, str] = {}
        self.cache_hits = 0
        self.cache_misses = 0

    async def scan_directory(
        self,
        max_depth: int = 10,
        include_hidden: bool = False,
        respect_gitignore: bool = True,
    ) -> None:
        """
        Scan the project directory and build file index.

        Args:
            max_depth: Maximum directory depth to scan
            include_hidden: Whether to include hidden files/directories
            respect_gitignore: Whether to respect .gitignore patterns
        """
        logger.info(f"Scanning project directory: {self.project_root}")

        try:
            # Load .gitignore if it exists and respect_gitignore is True
            if respect_gitignore:
                gitignore_path = self.project_root / ".gitignore"
                if gitignore_path.exists():
                    self.gitignore.load_gitignore(gitignore_path)
                    logger.debug("Loaded .gitignore patterns")

            # Reset stats
            self.stats = ProjectStats()
            self.files.clear()

            # Scan directory tree
            await self._scan_recursive(
                self.project_root,
                depth=0,
                max_depth=max_depth,
                include_hidden=include_hidden,
                respect_gitignore=respect_gitignore,
            )

            # Calculate statistics
            self._calculate_stats()

            logger.info(
                f"Scan complete: {self.stats.total_files} files found "
                f"({self.stats.text_files} text, {self.stats.binary_files} binary)"
            )

        except Exception as e:
            logger.error(f"Failed to scan directory: {e}")
            show_error(f"Failed to scan project directory: {e}")
            raise

    async def _scan_recursive(
        self,
        directory: Path,
        depth: int,
        max_depth: int,
        include_hidden: bool,
        respect_gitignore: bool,
    ) -> None:
        """Recursively scan directory tree."""
        if depth > max_depth:
            return

        try:
            # Get directory entries
            entries = list(directory.iterdir())

            for entry in entries:
                try:
                    # Skip hidden files/directories if not included
                    if not include_hidden and entry.name.startswith("."):
                        # Always include .gitignore and common config files
                        if entry.name not in {
                            ".gitignore",
                            ".gitattributes",
                            ".editorconfig",
                            ".env",
                        }:
                            continue

                    # Check default ignore patterns
                    if self._matches_default_ignore(entry.name):
                        self.stats.ignored_files += 1
                        continue

                    # Check gitignore patterns
                    if respect_gitignore and self.gitignore.is_ignored(
                        entry, entry.is_dir()
                    ):
                        self.stats.ignored_files += 1
                        continue

                    if entry.is_file():
                        await self._process_file(entry)
                    elif entry.is_dir():
                        # Recurse into subdirectory
                        await self._scan_recursive(
                            entry,
                            depth + 1,
                            max_depth,
                            include_hidden,
                            respect_gitignore,
                        )

                except (PermissionError, OSError) as e:
                    logger.debug(f"Skipping {entry}: {e}")
                    continue

        except (PermissionError, OSError) as e:
            logger.warning(f"Cannot access directory {directory}: {e}")

    async def _process_file(self, file_path: Path) -> None:
        """Process a single file and add to index."""
        try:
            stat = file_path.stat()

            # Skip very large files
            if stat.st_size > self.max_file_size:
                logger.debug(f"Skipping large file: {file_path} ({stat.st_size} bytes)")
                return

            # Create FileInfo
            file_info = FileInfo(
                path=file_path,
                relative_path=file_path.relative_to(self.project_root),
                size=stat.st_size,
                modified_time=datetime.fromtimestamp(stat.st_mtime),
                mime_type=None,  # Will be computed in __post_init__
                is_text=False,  # Will be computed in __post_init__
                is_binary=False,  # Will be computed in __post_init__
            )

            # Add to index
            self.files[file_path] = file_info

        except (OSError, ValueError) as e:
            logger.debug(f"Failed to process file {file_path}: {e}")

    def _matches_default_ignore(self, name: str) -> bool:
        """Check if filename matches default ignore patterns."""
        for pattern in self.default_ignore_patterns:
            if fnmatch.fnmatch(name, pattern):
                return True
        return False

    def _calculate_stats(self) -> None:
        """Calculate project statistics."""
        self.stats.total_files = len(self.files)

        for file_info in self.files.values():
            self.stats.total_size += file_info.size

            if file_info.is_text:
                self.stats.text_files += 1
            else:
                self.stats.binary_files += 1

            # Track languages by extension
            ext = file_info.path.suffix.lower()
            if ext:
                self.stats.languages[ext] = self.stats.languages.get(ext, 0) + 1

        # Find largest files
        sorted_files = sorted(
            [(info.path, info.size) for info in self.files.values()],
            key=lambda x: x[1],
            reverse=True,
        )
        self.stats.largest_files = sorted_files[:10]

    async def read_file_content(
        self, file_path: Path, force_reload: bool = False
    ) -> str | None:
        """
        Read and cache file content.

        Args:
            file_path: Path to the file
            force_reload: Whether to force reload from disk

        Returns:
            File content as string, or None if cannot read
        """
        try:
            # Check if file is in our index
            if file_path not in self.files:
                logger.warning(f"File not in index: {file_path}")
                return None

            file_info = self.files[file_path]

            # Skip binary files
            if file_info.is_binary:
                return None

            # Generate cache key
            cache_key = self._generate_cache_key(file_info)

            # Check cache first
            if not force_reload and cache_key in self.content_cache:
                self.cache_hits += 1
                return self.content_cache[cache_key]

            self.cache_misses += 1

            # Read file content
            content = await self._read_file_async(file_path)
            if content is not None:
                # Cache the content
                self.content_cache[cache_key] = content
                file_info.cached_content = content
                file_info.content_hash = cache_key

            return content

        except Exception as e:
            logger.error(f"Failed to read file {file_path}: {e}")
            return None

    async def _read_file_async(self, file_path: Path) -> str | None:
        """Asynchronously read file content."""
        try:
            loop = asyncio.get_event_loop()

            # Try different encodings
            encodings = ["utf-8", "utf-8-sig", "latin-1", "cp1252"]

            for encoding in encodings:
                try:

                    def read_with_encoding(enc=encoding):
                        return file_path.read_text(encoding=enc)

                    content = await loop.run_in_executor(None, read_with_encoding)

                    # Update file info with successful encoding
                    if file_path in self.files:
                        self.files[file_path].encoding = encoding

                    return content

                except UnicodeDecodeError:
                    continue

            # If all encodings fail, try reading as binary and decode with errors='ignore'
            try:
                binary_content = await loop.run_in_executor(
                    None, lambda: file_path.read_bytes()
                )
                content = binary_content.decode("utf-8", errors="ignore")

                if file_path in self.files:
                    self.files[file_path].encoding = "utf-8-with-errors"

                return content

            except Exception:
                logger.debug(f"Cannot read file as text: {file_path}")
                return None

        except Exception as e:
            logger.debug(f"Failed to read file {file_path}: {e}")
            return None

    def _generate_cache_key(self, file_info: FileInfo) -> str:
        """Generate cache key for file content."""
        # Use file path, size, and modification time
        key_data = (
            f"{file_info.path}:{file_info.size}:{file_info.modified_time.timestamp()}"
        )
        return hashlib.md5(key_data.encode()).hexdigest()

    def get_relevant_files(
        self,
        query: str | None = None,
        file_types: list[str] | None = None,
        max_files: int = 50,
    ) -> list[FileInfo]:
        """
        Get relevant files based on query and filters.

        Args:
            query: Search query for filenames/paths
            file_types: List of file extensions to include
            max_files: Maximum number of files to return

        Returns:
            List of relevant FileInfo objects
        """
        filtered_files = []

        for file_info in self.files.values():
            # Skip binary files
            if file_info.is_binary:
                continue

            # Filter by file types
            if file_types:
                ext = file_info.path.suffix.lower()
                if ext not in file_types:
                    continue

            # Filter by query
            if query:
                query_lower = query.lower()
                path_str = str(file_info.relative_path).lower()
                if query_lower not in path_str:
                    continue

            filtered_files.append(file_info)

        # Sort by relevance (prioritize shorter paths and common file types)
        def relevance_score(file_info: FileInfo) -> float:
            score = 0.0

            # Prefer shorter paths (closer to root)
            score -= len(file_info.relative_path.parts) * 0.1

            # Prefer common development files
            ext = file_info.path.suffix.lower()
            if ext in {".py", ".js", ".ts", ".jsx", ".tsx"}:
                score += 1.0
            elif ext in {".md", ".txt", ".json", ".yaml", ".yml"}:
                score += 0.5

            # Prefer config files
            if file_info.path.name in {
                "README.md",
                "setup.py",
                "package.json",
                "pyproject.toml",
            }:
                score += 2.0

            return score

        filtered_files.sort(key=relevance_score, reverse=True)

        return filtered_files[:max_files]

    async def build_context_prompt(
        self,
        query: str | None = None,
        include_file_contents: bool = True,
        max_context_length: int = 4000,
    ) -> str:
        """
        Build context prompt for LLM.

        Args:
            query: User query to focus context
            include_file_contents: Whether to include file contents
            max_context_length: Maximum context length in characters

        Returns:
            Formatted context string for LLM
        """
        context_parts = []
        current_length = 0

        # Add project overview
        overview = self._build_project_overview()
        context_parts.append(overview)
        current_length += len(overview)

        if current_length >= max_context_length:
            return "\n\n".join(context_parts)

        # Add file tree
        if current_length < max_context_length * 0.3:  # Use max 30% for tree
            tree_context = self._build_file_tree()
            if tree_context:
                context_parts.append(tree_context)
                current_length += len(tree_context)

        # Add relevant file contents
        if include_file_contents and current_length < max_context_length:
            relevant_files = self.get_relevant_files(query=query, max_files=10)

            for file_info in relevant_files:
                if current_length >= max_context_length * 0.8:  # Reserve 20% buffer
                    break

                content = await self.read_file_content(file_info.path)
                if content:
                    file_section = (
                        f"\n## File: {file_info.relative_path}\n```\n{content}\n```"
                    )

                    if current_length + len(file_section) < max_context_length:
                        context_parts.append(file_section)
                        current_length += len(file_section)
                    else:
                        # Truncate content to fit
                        remaining_space = (
                            max_context_length - current_length - 100
                        )  # Buffer
                        if remaining_space > 200:  # Minimum useful content
                            truncated_content = (
                                content[: remaining_space - 50] + "\n... (truncated)"
                            )
                            file_section = f"\n## File: {file_info.relative_path}\n```\n{truncated_content}\n```"
                            context_parts.append(file_section)
                        break

        return "\n\n".join(context_parts)

    def _build_project_overview(self) -> str:
        """Build project overview section."""
        overview = "# Project Overview\n\n"
        overview += f"**Project Root:** {self.project_root}\n"
        overview += f"**Total Files:** {self.stats.total_files}\n"
        overview += f"**Text Files:** {self.stats.text_files}\n"
        overview += f"**Total Size:** {self._format_size(self.stats.total_size)}\n\n"

        if self.stats.languages:
            overview += "**Languages/File Types:**\n"
            sorted_langs = sorted(
                self.stats.languages.items(), key=lambda x: x[1], reverse=True
            )
            for ext, count in sorted_langs[:10]:
                overview += f"- {ext}: {count} files\n"

        return overview

    def _build_file_tree(self, max_files: int = 100) -> str:
        """Build file tree representation."""
        if not self.files:
            return ""

        tree = Tree(f"{self.project_root.name}", guide_style="dim")
        added_files = 0

        # Group files by directory
        dirs: dict[Path, list[FileInfo]] = {}
        for file_info in self.files.values():
            if file_info.is_binary:
                continue

            dir_path = file_info.relative_path.parent
            if dir_path not in dirs:
                dirs[dir_path] = []
            dirs[dir_path].append(file_info)

            added_files += 1
            if added_files >= max_files:
                break

        # Build tree structure
        for dir_path in sorted(dirs.keys()):
            if dir_path == Path("."):
                # Root files
                for file_info in sorted(dirs[dir_path], key=lambda f: f.path.name):
                    tree.add(f"{file_info.path.name}")
            else:
                # Create directory node
                dir_node = tree.add(f"{dir_path}")
                for file_info in sorted(dirs[dir_path], key=lambda f: f.path.name):
                    dir_node.add(f"{file_info.path.name}")

        # Render tree to string
        with console.capture() as capture:
            console.print(tree)

        return f"# Project Structure\n\n```\n{capture.get()}\n```"

    def _format_size(self, size_bytes: int) -> str:
        """Format file size in human readable format."""
        for unit in ["B", "KB", "MB", "GB"]:
            if size_bytes < 1024:
                return f"{int(size_bytes):.1f} {unit}"
            size_bytes /= 1024
        return f"{int(size_bytes):.1f} TB"

    def get_cache_stats(self) -> dict[str, Any]:
        """Get cache performance statistics."""
        total_requests = self.cache_hits + self.cache_misses
        hit_rate = (self.cache_hits / total_requests * 100) if total_requests > 0 else 0

        return {
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "hit_rate_percent": hit_rate,
            "cached_files": len(self.content_cache),
            "cache_size_mb": sum(
                len(content.encode()) for content in self.content_cache.values()
            )
            / (1024 * 1024),
        }

    def clear_cache(self) -> None:
        """Clear content cache."""
        self.content_cache.clear()
        self.cache_hits = 0
        self.cache_misses = 0

        # Clear cached content from file info
        for file_info in self.files.values():
            file_info.cached_content = None
            file_info.content_hash = None

    def get_project_stats(self) -> ProjectStats:
        """Get project statistics."""
        return self.stats

    def get_files_by_type(self, file_extension: str) -> list[FileInfo]:
        """Get all files with a specific extension."""
        return [
            file_info
            for file_info in self.files.values()
            if file_info.path.suffix.lower() == file_extension.lower()
        ]

    def find_files(self, pattern: str) -> list[FileInfo]:
        """Find files matching a glob pattern."""
        matching_files = []

        for file_info in self.files.values():
            if fnmatch.fnmatch(str(file_info.relative_path), pattern):
                matching_files.append(file_info)

        return matching_files

    # Phase 8c: Dynamic Context Building Methods

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        """
        Estimate token count for text.

        Uses the rule of thumb: ~4 characters per token.

        Args:
            text: Text to estimate tokens for

        Returns:
            Estimated token count
        """
        return len(text) // 4

    def _prioritize_files(
        self,
        query: str | None = None,
        mentioned_files: list[Path] | None = None,
        recent_files: list[Path] | None = None,
    ) -> list[FileInfo]:
        """
        Prioritize files for context building.

        Priority order:
        1. Explicitly mentioned files
        2. Recently accessed/modified files
        3. Core project files (config, entry points)
        4. Other relevant files

        Args:
            query: User query to identify relevant files
            mentioned_files: Files explicitly mentioned in conversation
            recent_files: Recently accessed files

        Returns:
            Sorted list of FileInfo objects by priority
        """
        prioritized: list[tuple[FileInfo, float]] = []

        for file_info in self.files.values():
            # Skip binary files
            if file_info.is_binary:
                continue

            priority = 0.0

            # Priority 1: Explicitly mentioned files (highest)
            if mentioned_files:
                for mentioned in mentioned_files:
                    if file_info.path == mentioned or str(mentioned) in str(
                        file_info.path
                    ):
                        priority += 100.0
                        break

            # Priority 2: Recently accessed files
            if recent_files:
                for recent in recent_files:
                    if file_info.path == recent:
                        priority += 50.0
                        break

            # Priority 3: Core project files
            core_files = {
                "readme.md",
                "setup.py",
                "pyproject.toml",
                "package.json",
                "main.py",
                "__init__.py",
                "__main__.py",
                "app.py",
                "index.js",
                "index.ts",
            }
            if file_info.path.name.lower() in core_files:
                priority += 30.0

            # Priority 4: Query relevance
            if query:
                query_lower = query.lower()
                path_str = str(file_info.relative_path).lower()
                file_name = file_info.path.name.lower()

                # Filename match
                if query_lower in file_name:
                    priority += 20.0
                # Path match
                elif query_lower in path_str:
                    priority += 10.0

            # Priority 5: File type relevance
            ext = file_info.path.suffix.lower()
            if ext in {".py", ".js", ".ts", ".jsx", ".tsx"}:
                priority += 5.0
            elif ext in {".md", ".txt", ".json", ".yaml", ".yml"}:
                priority += 2.0

            # Priority 6: Recency (modification time)
            age_days = (
                datetime.now() - file_info.modified_time
            ).total_seconds() / 86400
            if age_days < 1:
                priority += 3.0
            elif age_days < 7:
                priority += 1.0

            # Priority 7: Proximity to root (prefer files closer to root)
            depth = len(file_info.relative_path.parts)
            priority += float(max(0, 5 - depth))

            prioritized.append((file_info, priority))

        # Sort by priority (descending)
        prioritized.sort(key=lambda x: x[1], reverse=True)

        return [file_info for file_info, _ in prioritized]

    async def _smart_context_building(
        self,
        max_tokens: int,
        query: str | None = None,
        mentioned_files: list[Path] | None = None,
        recent_files: list[Path] | None = None,
    ) -> str:
        """
        Build context using smart prioritization strategy.

        Reads files in priority order until token budget is exhausted.

        Args:
            max_tokens: Maximum tokens for context
            query: User query for relevance
            mentioned_files: Files explicitly mentioned
            recent_files: Recently accessed files

        Returns:
            Context string within token budget
        """
        context_parts = []
        current_tokens = 0

        # Add project overview (always include)
        overview = self._build_project_overview()
        overview_tokens = self._estimate_tokens(overview)
        context_parts.append(overview)
        current_tokens += overview_tokens

        # Reserve tokens for file tree (10% of budget)
        tree_budget = int(max_tokens * 0.1)
        if current_tokens + tree_budget < max_tokens:
            tree_context = self._build_file_tree()
            if tree_context:
                tree_tokens = self._estimate_tokens(tree_context)
                if tree_tokens <= tree_budget:
                    context_parts.append(tree_context)
                    current_tokens += tree_tokens

        # Prioritize files
        prioritized_files = self._prioritize_files(query, mentioned_files, recent_files)

        # Add files until token budget exhausted (reserve 5% for safety)
        token_limit = int(max_tokens * 0.95)

        for file_info in prioritized_files:
            if current_tokens >= token_limit:
                break

            content = await self.read_file_content(file_info.path)
            if not content:
                continue

            # Check if file fits
            file_tokens = self._estimate_tokens(content)
            header = f"\n## File: {file_info.relative_path}\n```\n"
            footer = "\n```"
            total_tokens = self._estimate_tokens(header + footer) + file_tokens

            if current_tokens + total_tokens <= token_limit:
                # Include full file
                file_section = f"{header}{content}{footer}"
                context_parts.append(file_section)
                current_tokens += total_tokens
            else:
                # Try to summarize/truncate
                remaining_tokens = token_limit - current_tokens - self._estimate_tokens(
                    header + footer
                )
                if remaining_tokens > 100:  # Minimum useful content
                    summarized = await self._summarize_file(content, remaining_tokens)
                    file_section = f"{header}{summarized}{footer}"
                    context_parts.append(file_section)
                    current_tokens += self._estimate_tokens(file_section)
                break

        logger.info(
            f"Smart context built: {current_tokens}/{max_tokens} tokens "
            f"({len(context_parts)} sections)"
        )

        return "\n\n".join(context_parts)

    async def _read_whole_repo_chunked(
        self, max_tokens: int, query: str | None = None
    ) -> str:
        """
        Read entire repository with intelligent chunking.

        Attempts to include all text files, summarizing as needed.

        Args:
            max_tokens: Maximum tokens for context
            query: Optional query for file ordering

        Returns:
            Context string with repository contents
        """
        context_parts = []
        current_tokens = 0

        # Add overview
        overview = self._build_project_overview()
        context_parts.append(overview)
        current_tokens += self._estimate_tokens(overview)

        # Get all text files
        all_files = [f for f in self.files.values() if not f.is_binary]

        # Sort by priority if query provided, otherwise by path
        if query:
            all_files = self._prioritize_files(query=query)
        else:
            all_files.sort(key=lambda f: str(f.relative_path))

        # Calculate average tokens per file
        token_budget = int(max_tokens * 0.95) - current_tokens
        tokens_per_file = token_budget // max(len(all_files), 1)

        for file_info in all_files:
            if current_tokens >= token_budget:
                break

            content = await self.read_file_content(file_info.path)
            if not content:
                continue

            file_tokens = self._estimate_tokens(content)
            header = f"\n## File: {file_info.relative_path}\n```\n"
            footer = "\n```"

            if file_tokens <= tokens_per_file:
                # Include full file
                file_section = f"{header}{content}{footer}"
            else:
                # Summarize to fit budget
                summarized = await self._summarize_file(content, tokens_per_file)
                file_section = f"{header}{summarized}{footer}"

            section_tokens = self._estimate_tokens(file_section)
            if current_tokens + section_tokens <= token_budget:
                context_parts.append(file_section)
                current_tokens += section_tokens

        logger.info(
            f"Whole repo context built: {current_tokens}/{max_tokens} tokens "
            f"({len(all_files)} files)"
        )

        return "\n\n".join(context_parts)

    async def _iterative_reading(
        self, max_tokens: int, max_iterations: int = 10
    ) -> str:
        """
        Build context iteratively, expanding based on previous content.

        This is a placeholder for future LLM-guided iterative reading.

        Args:
            max_tokens: Maximum tokens for context
            max_iterations: Maximum number of iterations

        Returns:
            Context string built iteratively
        """
        # For now, use smart context building as fallback
        logger.info(
            f"Iterative reading (max {max_iterations} iterations) - "
            "using smart strategy as fallback"
        )
        return await self._smart_context_building(max_tokens)

    async def _summarize_file(self, content: str, max_tokens: int) -> str:
        """
        Summarize or truncate file content to fit token budget.

        Args:
            content: Full file content
            max_tokens: Maximum tokens allowed

        Returns:
            Summarized/truncated content
        """
        max_chars = max_tokens * 4  # Approximate characters

        if len(content) <= max_chars:
            return content

        # Smart truncation strategies
        lines = content.split("\n")

        # Strategy 1: Include beginning and end
        if len(lines) > 20:
            # Calculate how many lines we can fit
            avg_line_length = len(content) // len(lines)
            max_lines = max_chars // max(avg_line_length, 1)

            if max_lines >= 10:
                # Take first 60% and last 20%
                start_lines = int(max_lines * 0.6)
                end_lines = int(max_lines * 0.2)

                start_content = "\n".join(lines[:start_lines])
                end_content = "\n".join(lines[-end_lines:])

                omitted_lines = len(lines) - start_lines - end_lines

                return (
                    f"{start_content}\n\n"
                    f"... [{omitted_lines} lines omitted] ...\n\n"
                    f"{end_content}"
                )

        # Strategy 2: Simple truncation
        truncated = content[:max_chars]
        return f"{truncated}\n\n... [truncated, {len(content) - max_chars} chars omitted]"

    async def build_dynamic_context(
        self,
        query: str | None = None,
        max_tokens: int = 4000,
        strategy: str = "smart",
        mentioned_files: list[Path] | None = None,
        recent_files: list[Path] | None = None,
    ) -> str:
        """
        Build context dynamically based on token budget and strategy.

        Main orchestrator for Phase 8c context building.

        Args:
            query: User query for context relevance
            max_tokens: Maximum tokens for context (based on model capability)
            strategy: Context building strategy ('smart', 'whole_repo', 'iterative', 'off')
            mentioned_files: Files explicitly mentioned in conversation
            recent_files: Recently accessed files

        Returns:
            Context string within token budget
        """
        if strategy == "off":
            return ""

        logger.info(
            f"Building dynamic context: strategy={strategy}, max_tokens={max_tokens}"
        )

        try:
            if strategy == "smart":
                return await self._smart_context_building(
                    max_tokens, query, mentioned_files, recent_files
                )
            elif strategy == "whole_repo":
                return await self._read_whole_repo_chunked(max_tokens, query)
            elif strategy == "iterative":
                return await self._iterative_reading(max_tokens)
            else:
                logger.warning(f"Unknown strategy '{strategy}', using 'smart'")
                return await self._smart_context_building(
                    max_tokens, query, mentioned_files, recent_files
                )

        except Exception as e:
            logger.error(f"Failed to build dynamic context: {e}")
            # Fallback to basic context
            return await self.build_context_prompt(
                query=query, max_context_length=max_tokens * 4
            )
