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
            "priority": self.priority.value
            if isinstance(self.priority, SuggestionPriority)
            else self.priority,
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

    def __init__(self, complexity_detector=None, clarification_engine=None):
        """
        Initialize the suggestor with optional intelligence systems.

        Args:
            complexity_detector: Optional ComplexityDetector for task analysis
            clarification_engine: Optional ClarificationEngine for ambiguity detection
        """
        self.complexity_detector = complexity_detector
        self.clarification_engine = clarification_engine
        self.suggestion_patterns = self._build_patterns()

    def _build_patterns(self) -> dict[str, list[dict[str, Any]]]:
        """Build pattern definitions for suggestions."""
        return {
            "testing": [
                {
                    "trigger": lambda code: "def " in code and "test_" not in code,
                    "priority": SuggestionPriority.HIGH,
                    "title": "Add unit tests",
                    "description": "This file contains functions but no tests. Consider adding unit tests.",
                    "benefits": [
                        "Catch bugs early",
                        "Document behavior",
                        "Enable safe refactoring",
                    ],
                },
                {
                    "trigger": lambda code: "class " in code and "Test" not in code,
                    "priority": SuggestionPriority.HIGH,
                    "title": "Add class tests",
                    "description": "This class could benefit from unit tests to ensure correctness.",
                    "benefits": [
                        "Verify class behavior",
                        "Prevent regressions",
                        "Improve confidence",
                    ],
                },
            ],
            "documentation": [
                {
                    "trigger": lambda code: "def " in code
                    and '"""' not in code
                    and "'''" not in code,
                    "priority": SuggestionPriority.MEDIUM,
                    "title": "Add docstrings",
                    "description": "Functions are missing docstrings. Add documentation for better maintainability.",
                    "benefits": [
                        "Improve code understanding",
                        "Enable auto-documentation",
                        "Help IDE autocomplete",
                    ],
                },
                {
                    "trigger": lambda code: "class " in code
                    and '"""' not in code
                    and "'''" not in code,
                    "priority": SuggestionPriority.MEDIUM,
                    "title": "Add class documentation",
                    "description": "Classes should have docstrings explaining their purpose and usage.",
                    "benefits": [
                        "Document class purpose",
                        "Explain usage patterns",
                        "Aid new developers",
                    ],
                },
                {
                    "trigger": lambda code: "# TODO" in code or "# FIXME" in code,
                    "priority": SuggestionPriority.LOW,
                    "title": "Address TODOs",
                    "description": "This file contains TODO or FIXME comments that should be addressed.",
                    "benefits": [
                        "Complete unfinished work",
                        "Improve code quality",
                        "Remove technical debt",
                    ],
                },
            ],
            "error_handling": [
                {
                    "trigger": lambda code: "open(" in code and "try:" not in code,
                    "priority": SuggestionPriority.HIGH,
                    "title": "Add error handling for file operations",
                    "description": "File operations should be wrapped in try-except blocks.",
                    "benefits": [
                        "Prevent crashes",
                        "Handle errors gracefully",
                        "Improve robustness",
                    ],
                },
                {
                    "trigger": lambda code: ("requests." in code or "httpx." in code)
                    and "try:" not in code,
                    "priority": SuggestionPriority.HIGH,
                    "title": "Add error handling for network requests",
                    "description": "Network requests should handle exceptions for robustness.",
                    "benefits": [
                        "Handle network failures",
                        "Improve reliability",
                        "Better user experience",
                    ],
                },
                {
                    "trigger": lambda code: "raise Exception(" in code,
                    "priority": SuggestionPriority.MEDIUM,
                    "title": "Use specific exception types",
                    "description": "Consider using specific exception types instead of generic Exception.",
                    "benefits": [
                        "Better error handling",
                        "Clearer intent",
                        "Easier debugging",
                    ],
                },
            ],
            "performance": [
                {
                    "trigger": lambda code: "for " in code and " in range(len(" in code,
                    "priority": SuggestionPriority.LOW,
                    "title": "Consider enumerate()",
                    "description": "Use enumerate() instead of range(len()) for better readability.",
                    "benefits": [
                        "Improved readability",
                        "More Pythonic",
                        "Clearer intent",
                    ],
                },
                {
                    "trigger": lambda code: code.count("import ") > 20,
                    "priority": SuggestionPriority.LOW,
                    "title": "Review import count",
                    "description": "Large number of imports may indicate the module is doing too much.",
                    "benefits": [
                        "Better modularity",
                        "Clearer responsibilities",
                        "Easier maintenance",
                    ],
                },
            ],
            "security": [
                {
                    "trigger": lambda code: "eval(" in code or "exec(" in code,
                    "priority": SuggestionPriority.CRITICAL,
                    "title": "Avoid eval() and exec()",
                    "description": "Using eval() or exec() is a security risk. Consider safer alternatives.",
                    "benefits": [
                        "Improved security",
                        "Prevent code injection",
                        "Safer execution",
                    ],
                },
                {
                    "trigger": lambda code: "password" in code.lower() and '"' in code,
                    "priority": SuggestionPriority.CRITICAL,
                    "title": "Avoid hardcoded credentials",
                    "description": "Passwords or secrets should not be hardcoded in source files.",
                    "benefits": [
                        "Enhanced security",
                        "Easier credential rotation",
                        "No secrets in VCS",
                    ],
                },
                {
                    "trigger": lambda code: "shell=True" in code
                    and "subprocess" in code,
                    "priority": SuggestionPriority.CRITICAL,
                    "title": "Avoid shell=True in subprocess",
                    "description": "Using shell=True with subprocess is a security risk for command injection.",
                    "benefits": [
                        "Prevent command injection",
                        "Improved security",
                        "Safer subprocess execution",
                    ],
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
                            suggestion_type=category,
                            priority=pattern_def["priority"],
                            title=pattern_def["title"],
                            description=pattern_def["description"],
                            reasoning=f"Pattern detected in {file_path.name}",
                            affected_files=[str(file_path)],
                            benefits=pattern_def.get("benefits", []),
                            file_path=str(file_path),  # Backwards compatibility
                        )
                        suggestions.append(suggestion)
                except Exception as e:
                    logger.warning(f"Pattern check failed: {e}")

        return suggestions

    def analyze_project_structure(
        self, files: dict[str, Any], context: dict[str, Any]
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
                "priority": SuggestionPriority.HIGH,
                "title": "Add README.md",
                "description": "Projects should have a README explaining purpose and usage.",
                "benefits": [
                    "Better documentation",
                    "Easier onboarding",
                    "Project visibility",
                ],
            },
            "requirements.txt": {
                "priority": SuggestionPriority.MEDIUM,
                "title": "Add requirements.txt",
                "description": "Python projects should list dependencies in requirements.txt.",
                "benefits": [
                    "Reproducible environment",
                    "Clear dependencies",
                    "Easier deployment",
                ],
            },
            ".gitignore": {
                "priority": SuggestionPriority.MEDIUM,
                "title": "Add .gitignore",
                "description": "Projects should have .gitignore to exclude unnecessary files.",
                "benefits": [
                    "Cleaner repository",
                    "No sensitive data",
                    "Faster operations",
                ],
            },
            "tests": {
                "priority": SuggestionPriority.HIGH,
                "title": "Add tests directory",
                "description": "Projects should have a dedicated tests directory.",
                "benefits": [
                    "Organized testing",
                    "Better test discovery",
                    "Clear structure",
                ],
            },
        }

        file_paths = [str(f) for f in files.keys()] if files else []

        for file_name, suggestion_data in common_files.items():
            # Check if file exists
            if not any(file_name in path for path in file_paths):
                suggestion = Suggestion(
                    suggestion_type=SuggestionType.PROJECT_STRUCTURE,
                    priority=suggestion_data["priority"],
                    title=suggestion_data["title"],
                    description=suggestion_data["description"],
                    reasoning=f"Missing {file_name} in project",
                    benefits=suggestion_data["benefits"],
                )
                suggestions.append(suggestion)

        return suggestions

    def suggest_after_edit(
        self, file_path: Path, operation: str, content: str | None = None
    ) -> list[Suggestion]:
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
        if (
            operation == "create"
            and file_path.suffix == ".py"
            and "test_" not in file_path.name
        ):
            suggestions.append(
                Suggestion(
                    suggestion_type=SuggestionType.TESTING,
                    priority=SuggestionPriority.HIGH,
                    title="Create tests for new file",
                    description=f"Consider creating test_{file_path.stem}.py to test this new module.",
                    reasoning="New modules should have corresponding test files",
                    affected_files=[str(file_path)],
                    benefits=[
                        "Ensure correctness",
                        "Prevent regressions",
                        "Document expected behavior",
                    ],
                    file_path=str(file_path),
                )
            )

        # Suggest documentation for new modules
        if operation == "create" and file_path.suffix == ".py":
            suggestions.append(
                Suggestion(
                    suggestion_type=SuggestionType.DOCUMENTATION,
                    priority=SuggestionPriority.MEDIUM,
                    title="Document new module",
                    description="Add a module-level docstring explaining the purpose of this file.",
                    reasoning="Module docstrings improve code understanding",
                    affected_files=[str(file_path)],
                    benefits=[
                        "Better documentation",
                        "Easier onboarding",
                        "Clear purpose",
                    ],
                    file_path=str(file_path),
                )
            )

        return suggestions

    def suggest_for_task(
        self, user_input: str, complexity_analysis: Any | None = None
    ) -> list[Suggestion]:
        """
        Generate suggestions for a specific task using intelligence systems.

        This method integrates with complexity detector and clarification engine
        to provide contextually relevant suggestions.

        Args:
            user_input: User's task description
            complexity_analysis: Optional complexity analysis from ComplexityDetector

        Returns:
            List of task-specific suggestions
        """
        suggestions = []

        # Suggest planning for complex tasks
        if complexity_analysis:
            if (
                hasattr(complexity_analysis, "requires_planning")
                and complexity_analysis.requires_planning
            ):
                suggestions.append(
                    Suggestion(
                        suggestion_type=SuggestionType.PLANNING,
                        priority=SuggestionPriority.HIGH,
                        title="Use multi-step planning",
                        description="This task is complex and would benefit from a structured plan",
                        reasoning=f"Complexity level: {complexity_analysis.complexity_level.value}, "
                        f"estimated {complexity_analysis.resource_estimate.estimated_steps} steps",
                        action_command="/plan",
                        estimated_time=5,
                        benefits=[
                            "Better organization of work",
                            "Reduced risk of errors",
                            "Clear progress tracking",
                        ],
                        metadata={
                            "complexity_score": complexity_analysis.complexity_score
                        },
                    )
                )

            # Suggest confirmation for high-risk
            if (
                hasattr(complexity_analysis, "requires_confirmation")
                and complexity_analysis.requires_confirmation
            ):
                suggestions.append(
                    Suggestion(
                        suggestion_type=SuggestionType.CONFIRMATION,
                        priority=SuggestionPriority.CRITICAL,
                        title="Review operation before proceeding",
                        description="This operation has high risk and requires careful review",
                        reasoning=f"Risk level: {complexity_analysis.risk_level.value}",
                        estimated_time=2,
                        benefits=[
                            "Avoid unintended consequences",
                            "Verify operation scope",
                            "Create backup before changes",
                        ],
                        metadata={"risk_level": complexity_analysis.risk_level.value},
                    )
                )

        # Suggest clarification for ambiguous tasks
        ambiguous_patterns = [
            "this",
            "that",
            "everything",
            "all files",
            "fix",
            "improve",
            "better",
        ]
        detected_ambiguous = [p for p in ambiguous_patterns if p in user_input.lower()]

        if detected_ambiguous and len(detected_ambiguous) >= 2:
            suggestions.append(
                Suggestion(
                    suggestion_type=SuggestionType.CLARIFICATION,
                    priority=SuggestionPriority.MEDIUM,
                    title="Clarify task scope",
                    description="The task description contains ambiguous terms",
                    reasoning="Ambiguous terms detected: "
                    + ", ".join(detected_ambiguous),
                    estimated_time=1,
                    benefits=[
                        "Ensure correct interpretation",
                        "Avoid wasted effort",
                        "Better results",
                    ],
                )
            )

        # Suggest testing for code changes
        if any(
            keyword in user_input.lower()
            for keyword in ["add", "implement", "create", "refactor", "change"]
        ):
            suggestions.append(
                Suggestion(
                    suggestion_type=SuggestionType.TESTING,
                    priority=SuggestionPriority.MEDIUM,
                    title="Add tests for changes",
                    description="Consider adding tests to verify the implementation",
                    reasoning="Code changes should be accompanied by tests",
                    estimated_time=10,
                    benefits=[
                        "Catch bugs early",
                        "Document expected behavior",
                        "Enable safe refactoring",
                    ],
                )
            )

        # Suggest documentation for new features
        if any(
            keyword in user_input.lower()
            for keyword in ["new feature", "add feature", "implement"]
        ):
            suggestions.append(
                Suggestion(
                    suggestion_type=SuggestionType.DOCUMENTATION,
                    priority=SuggestionPriority.LOW,
                    title="Document new feature",
                    description="Update documentation to reflect the new feature",
                    reasoning="New features should be documented",
                    estimated_time=5,
                    benefits=[
                        "Better user understanding",
                        "Easier adoption",
                        "Complete documentation",
                    ],
                )
            )

        return suggestions

    def filter_suggestions(
        self,
        suggestions: list[Suggestion],
        max_count: int = 3,
        min_priority: str | SuggestionPriority = "low",
    ) -> list[Suggestion]:
        """Filter and prioritize suggestions.

        Args:
            suggestions: List of suggestions
            max_count: Maximum number of suggestions to return
            min_priority: Minimum priority level

        Returns:
            Filtered list of suggestions
        """
        # Priority ranking
        priority_rank = {
            SuggestionPriority.CRITICAL: 4,
            SuggestionPriority.HIGH: 3,
            SuggestionPriority.MEDIUM: 2,
            SuggestionPriority.LOW: 1,
            "critical": 4,  # Backwards compatibility
            "high": 3,
            "medium": 2,
            "low": 1,
        }

        # Convert string to enum if needed
        if isinstance(min_priority, str):
            try:
                min_priority = SuggestionPriority(min_priority)
            except ValueError:
                pass

        min_rank = priority_rank.get(min_priority, 1)

        # Filter by priority
        def get_priority_rank(s: Suggestion) -> int:
            if isinstance(s.priority, SuggestionPriority):
                return priority_rank.get(s.priority, 0)
            return priority_rank.get(s.priority, 0)

        filtered = [s for s in suggestions if get_priority_rank(s) >= min_rank]

        # Sort by priority (highest first)
        filtered.sort(key=get_priority_rank, reverse=True)

        # Limit count
        return filtered[:max_count]
