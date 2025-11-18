"""
Proactive Suggestions System for GerdsenAI CLI (Phase 8d-7).

This module implements intelligent, context-aware suggestions based on codebase
patterns, best practices, and integration with complexity/clarification/confirmation systems.

Provides frontier-level proactive assistance with non-intrusive, contextual recommendations.
"""

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class SuggestionType(Enum):
    """Types of proactive suggestions."""

    # Code quality suggestions
    REFACTORING = "refactoring"
    TESTING = "testing"
    DOCUMENTATION = "documentation"
    BEST_PRACTICE = "best_practice"
    PERFORMANCE = "performance"
    SECURITY = "security"

    # Workflow suggestions
    PLANNING = "planning"
    CLARIFICATION = "clarification"
    CONFIRMATION = "confirmation"

    # Improvement suggestions
    CODE_SMELL = "code_smell"
    DUPLICATE_CODE = "duplicate_code"
    COMPLEXITY_REDUCTION = "complexity_reduction"
    ERROR_HANDLING = "error_handling"
    PROJECT_STRUCTURE = "project_structure"


class SuggestionPriority(Enum):
    """Priority levels for suggestions."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Suggestion:
    """Individual suggestion with comprehensive context."""

    suggestion_type: SuggestionType | str  # Allow both for backwards compatibility
    priority: SuggestionPriority | str
    title: str
    description: str
    reasoning: str = ""
    affected_files: list[str] = field(default_factory=list)
    code_example: str | None = None
    action_command: str | None = None
    estimated_time: int = 5  # minutes
    benefits: list[str] = field(default_factory=list)
    file_path: str | None = None  # Backwards compatibility
    code_context: str | None = None  # Backwards compatibility
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Normalize types for backwards compatibility."""
        # Convert string types to enums
        if isinstance(self.suggestion_type, str):
            # Try to match to existing enum or use as-is
            try:
                self.suggestion_type = SuggestionType(self.suggestion_type)
            except ValueError:
                # Keep as string for backwards compatibility
                pass

        if isinstance(self.priority, str):
            try:
                self.priority = SuggestionPriority(self.priority)
            except ValueError:
                pass

        # Backwards compatibility: populate affected_files from file_path
        if self.file_path and not self.affected_files:
            self.affected_files = [self.file_path]

    @property
    def category(self) -> str:
        """Backwards compatibility property."""
        if isinstance(self.suggestion_type, SuggestionType):
            return self.suggestion_type.value
        return str(self.suggestion_type)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "suggestion_type": self.category,
            "category": self.category,  # Backwards compatibility
            "priority": self.priority.value if isinstance(self.priority, SuggestionPriority) else self.priority,
            "title": self.title,
            "description": self.description,
            "reasoning": self.reasoning,
            "affected_files": self.affected_files,
            "code_example": self.code_example,
            "action_command": self.action_command,
            "estimated_time": self.estimated_time,
            "benefits": self.benefits,
            "file_path": self.file_path,
            "code_context": self.code_context,
            "metadata": self.metadata,
        }


class ProactiveSuggestor:
    """Generates context-aware suggestions for code improvements."""
    
    def __init__(self):
        """Initialize the suggestor."""
        self.suggestion_patterns = self._build_patterns()
    
    def _build_patterns(self) -> dict[str, list[dict[str, Any]]]:
        """Build pattern definitions for suggestions."""
        return {
            "testing": [
                {
                    "trigger": lambda code: "def " in code and "test_" not in code,
                    "priority": "high",
                    "title": "Add unit tests",
                    "description": "This file contains functions but no tests. Consider adding unit tests.",
                },
                {
                    "trigger": lambda code: "class " in code and "Test" not in code,
                    "priority": "high",
                    "title": "Add class tests",
                    "description": "This class could benefit from unit tests to ensure correctness.",
                },
            ],
            "documentation": [
                {
                    "trigger": lambda code: 'def ' in code and '"""' not in code and "'''" not in code,
                    "priority": "medium",
                    "title": "Add docstrings",
                    "description": "Functions are missing docstrings. Add documentation for better maintainability.",
                },
                {
                    "trigger": lambda code: 'class ' in code and '"""' not in code and "'''" not in code,
                    "priority": "medium",
                    "title": "Add class documentation",
                    "description": "Classes should have docstrings explaining their purpose and usage.",
                },
                {
                    "trigger": lambda code: "# TODO" in code or "# FIXME" in code,
                    "priority": "low",
                    "title": "Address TODOs",
                    "description": "This file contains TODO or FIXME comments that should be addressed.",
                },
            ],
            "error_handling": [
                {
                    "trigger": lambda code: "open(" in code and "try:" not in code,
                    "priority": "high",
                    "title": "Add error handling for file operations",
                    "description": "File operations should be wrapped in try-except blocks.",
                },
                {
                    "trigger": lambda code: ("requests." in code or "httpx." in code) and "try:" not in code,
                    "priority": "high",
                    "title": "Add error handling for network requests",
                    "description": "Network requests should handle exceptions for robustness.",
                },
                {
                    "trigger": lambda code: "raise Exception(" in code,
                    "priority": "medium",
                    "title": "Use specific exception types",
                    "description": "Consider using specific exception types instead of generic Exception.",
                },
            ],
            "performance": [
                {
                    "trigger": lambda code: "for " in code and " in range(len(" in code,
                    "priority": "low",
                    "title": "Consider enumerate()",
                    "description": "Use enumerate() instead of range(len()) for better readability.",
                },
                {
                    "trigger": lambda code: code.count("import ") > 20,
                    "priority": "low",
                    "title": "Review import count",
                    "description": "Large number of imports may indicate the module is doing too much.",
                },
            ],
            "security": [
                {
                    "trigger": lambda code: "eval(" in code or "exec(" in code,
                    "priority": "high",
                    "title": "Avoid eval() and exec()",
                    "description": "Using eval() or exec() is a security risk. Consider safer alternatives.",
                },
                {
                    "trigger": lambda code: "password" in code.lower() and '"' in code,
                    "priority": "high",
                    "title": "Avoid hardcoded credentials",
                    "description": "Passwords or secrets should not be hardcoded in source files.",
                },
            ],
        }
    
    def analyze_file(self, file_path: Path, content: str) -> list[Suggestion]:
        """Analyze a file and generate suggestions.
        
        Args:
            file_path: Path to the file
            content: File content
            
        Returns:
            List of suggestions
        """
        suggestions = []
        
        # Only analyze Python files for now
        if not file_path.suffix == ".py":
            return suggestions
        
        # Check each pattern category
        for category, patterns in self.suggestion_patterns.items():
            for pattern_def in patterns:
                try:
                    if pattern_def["trigger"](content):
                        suggestion = Suggestion(
                            category=category,
                            priority=pattern_def["priority"],
                            title=pattern_def["title"],
                            description=pattern_def["description"],
                            file_path=str(file_path),
                        )
                        suggestions.append(suggestion)
                except Exception as e:
                    logger.warning(f"Pattern check failed: {e}")
        
        return suggestions
    
    def analyze_project_structure(
        self,
        files: dict[str, Any],
        context: dict[str, Any]
    ) -> list[Suggestion]:
        """Analyze project structure and suggest improvements.
        
        Args:
            files: Dictionary of project files
            context: Project context information
            
        Returns:
            List of suggestions
        """
        suggestions = []
        
        # Check for missing common files
        common_files = {
            "README.md": {
                "priority": "high",
                "title": "Add README.md",
                "description": "Projects should have a README explaining purpose and usage.",
            },
            "requirements.txt": {
                "priority": "medium",
                "title": "Add requirements.txt",
                "description": "Python projects should list dependencies in requirements.txt.",
            },
            ".gitignore": {
                "priority": "medium",
                "title": "Add .gitignore",
                "description": "Projects should have .gitignore to exclude unnecessary files.",
            },
            "tests": {
                "priority": "high",
                "title": "Add tests directory",
                "description": "Projects should have a dedicated tests directory.",
            },
        }
        
        file_paths = [str(f) for f in files.keys()] if files else []
        
        for file_name, suggestion_data in common_files.items():
            # Check if file exists
            if not any(file_name in path for path in file_paths):
                suggestion = Suggestion(
                    category="project_structure",
                    priority=suggestion_data["priority"],
                    title=suggestion_data["title"],
                    description=suggestion_data["description"],
                )
                suggestions.append(suggestion)
        
        return suggestions
    
    def suggest_after_edit(self, file_path: Path, operation: str, content: str | None = None) -> list[Suggestion]:
        """Generate suggestions after a file edit.
        
        Args:
            file_path: Path to edited file
            operation: Type of operation (create, modify, delete)
            content: New file content (if available)
            
        Returns:
            List of suggestions
        """
        suggestions = []
        
        # Analyze the file if we have content
        if content and operation in ["create", "modify"]:
            suggestions.extend(self.analyze_file(file_path, content))
        
        # Suggest creating tests for new files
        if operation == "create" and file_path.suffix == ".py" and "test_" not in file_path.name:
            suggestions.append(Suggestion(
                category="testing",
                priority="high",
                title="Create tests for new file",
                description=f"Consider creating test_{file_path.stem}.py to test this new module.",
                file_path=str(file_path),
            ))
        
        # Suggest documentation for new modules
        if operation == "create" and file_path.suffix == ".py":
            suggestions.append(Suggestion(
                category="documentation",
                priority="medium",
                title="Document new module",
                description="Add a module-level docstring explaining the purpose of this file.",
                file_path=str(file_path),
            ))
        
        return suggestions
    
    def filter_suggestions(
        self,
        suggestions: list[Suggestion],
        max_count: int = 3,
        min_priority: str = "low"
    ) -> list[Suggestion]:
        """Filter and prioritize suggestions.
        
        Args:
            suggestions: List of suggestions
            max_count: Maximum number of suggestions to return
            min_priority: Minimum priority level ("high", "medium", "low")
            
        Returns:
            Filtered list of suggestions
        """
        # Priority ranking
        priority_rank = {"high": 3, "medium": 2, "low": 1}
        min_rank = priority_rank.get(min_priority, 1)
        
        # Filter by priority
        filtered = [s for s in suggestions if priority_rank.get(s.priority, 0) >= min_rank]
        
        # Sort by priority (high first)
        filtered.sort(key=lambda s: priority_rank.get(s.priority, 0), reverse=True)
        
        # Limit count
        return filtered[:max_count]
