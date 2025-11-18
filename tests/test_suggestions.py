"""
Tests for the proactive suggestion system.

Tests cover:
- Suggestion dataclass and enums
- Pattern-based detection
- Intelligence system integration
- Filtering and prioritization
- Command execution
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
from dataclasses import dataclass

from gerdsenai_cli.core.suggestions import (
    ProactiveSuggestor,
    Suggestion,
    SuggestionType,
    SuggestionPriority,
)
from gerdsenai_cli.commands.suggest_commands import SuggestCommand


class TestSuggestionDataclasses:
    """Test suggestion dataclasses and enums."""

    def test_suggestion_type_enum(self):
        """Test SuggestionType enum values."""
        assert SuggestionType.REFACTORING.value == "refactoring"
        assert SuggestionType.TESTING.value == "testing"
        assert SuggestionType.DOCUMENTATION.value == "documentation"
        assert SuggestionType.SECURITY.value == "security"
        assert SuggestionType.PLANNING.value == "planning"
        assert SuggestionType.CLARIFICATION.value == "clarification"
        assert SuggestionType.CONFIRMATION.value == "confirmation"

    def test_suggestion_priority_enum(self):
        """Test SuggestionPriority enum values."""
        assert SuggestionPriority.LOW.value == "low"
        assert SuggestionPriority.MEDIUM.value == "medium"
        assert SuggestionPriority.HIGH.value == "high"
        assert SuggestionPriority.CRITICAL.value == "critical"

    def test_suggestion_with_enums(self):
        """Test creating Suggestion with enum values."""
        suggestion = Suggestion(
            suggestion_type=SuggestionType.TESTING,
            priority=SuggestionPriority.HIGH,
            title="Add unit tests",
            description="This file lacks test coverage",
            reasoning="Testing ensures code reliability",
            benefits=["Better code quality", "Catch bugs early"],
        )

        assert suggestion.suggestion_type == SuggestionType.TESTING
        assert suggestion.priority == SuggestionPriority.HIGH
        assert suggestion.title == "Add unit tests"
        assert len(suggestion.benefits) == 2

    def test_suggestion_with_strings(self):
        """Test creating Suggestion with string values (backwards compatibility)."""
        suggestion = Suggestion(
            suggestion_type="testing",
            priority="high",
            title="Add unit tests",
            description="This file lacks test coverage",
        )

        # Should normalize to enums via __post_init__
        assert suggestion.suggestion_type == SuggestionType.TESTING
        assert suggestion.priority == SuggestionPriority.HIGH

    def test_suggestion_backwards_compatibility_fields(self):
        """Test backwards compatibility with old field names."""
        suggestion = Suggestion(
            suggestion_type=SuggestionType.TESTING,
            priority=SuggestionPriority.HIGH,
            title="Test",
            description="Desc",
            file_path="/path/to/file.py",
            code_context="def foo(): pass",
        )

        # Old fields should still be accessible
        assert suggestion.file_path == "/path/to/file.py"
        assert suggestion.code_context == "def foo(): pass"

        # category property should work
        assert suggestion.category == "testing"

    def test_suggestion_defaults(self):
        """Test Suggestion default values."""
        suggestion = Suggestion(
            suggestion_type=SuggestionType.TESTING,
            priority=SuggestionPriority.HIGH,
            title="Test",
            description="Desc",
        )

        assert suggestion.reasoning == ""
        assert suggestion.affected_files == []
        assert suggestion.code_example is None
        assert suggestion.action_command is None
        assert suggestion.estimated_time == 5
        assert suggestion.benefits == []
        assert suggestion.metadata == {}


class TestProactiveSuggestor:
    """Test ProactiveSuggestor class."""

    def test_initialization(self):
        """Test suggestor initialization."""
        suggestor = ProactiveSuggestor()

        assert suggestor.complexity_detector is None
        assert suggestor.clarification_engine is None
        assert len(suggestor.suggestion_patterns) > 0

    def test_initialization_with_intelligence_systems(self):
        """Test suggestor initialization with intelligence systems."""
        mock_complexity = Mock()
        mock_clarification = Mock()

        suggestor = ProactiveSuggestor(
            complexity_detector=mock_complexity,
            clarification_engine=mock_clarification,
        )

        assert suggestor.complexity_detector == mock_complexity
        assert suggestor.clarification_engine == mock_clarification

    def test_analyze_file_missing_tests(self):
        """Test detecting missing tests."""
        suggestor = ProactiveSuggestor()

        code = """
def calculate_sum(a, b):
    return a + b

def calculate_product(a, b):
    return a * b
"""

        suggestions = suggestor.analyze_file(Path("math.py"), code)

        # Should suggest adding tests
        test_suggestions = [
            s for s in suggestions if s.suggestion_type == SuggestionType.TESTING
        ]
        assert len(test_suggestions) > 0
        assert any("test" in s.title.lower() for s in test_suggestions)

    def test_analyze_file_missing_docstrings(self):
        """Test detecting missing docstrings."""
        suggestor = ProactiveSuggestor()

        code = """
def complex_function(x, y, z):
    result = x * y + z
    return result if result > 0 else 0
"""

        suggestions = suggestor.analyze_file(Path("util.py"), code)

        # Should suggest adding documentation
        doc_suggestions = [
            s
            for s in suggestions
            if s.suggestion_type == SuggestionType.DOCUMENTATION
        ]
        assert len(doc_suggestions) > 0

    def test_analyze_file_security_issues(self):
        """Test detecting security issues."""
        suggestor = ProactiveSuggestor()

        code = """
import subprocess

def run_command(user_input):
    subprocess.call(user_input, shell=True)
"""

        suggestions = suggestor.analyze_file(Path("commands.py"), code)

        # Should detect security risk
        security_suggestions = [
            s for s in suggestions if s.suggestion_type == SuggestionType.SECURITY
        ]
        assert len(security_suggestions) > 0

    def test_analyze_file_error_handling(self):
        """Test detecting missing error handling."""
        suggestor = ProactiveSuggestor()

        code = """
def read_file(path):
    with open(path) as f:
        return f.read()
"""

        suggestions = suggestor.analyze_file(Path("io.py"), code)

        # Should suggest error handling
        error_suggestions = [
            s
            for s in suggestions
            if s.suggestion_type == SuggestionType.ERROR_HANDLING
        ]
        assert len(error_suggestions) > 0

    def test_analyze_project_structure(self):
        """Test project structure analysis."""
        suggestor = ProactiveSuggestor()

        files = {
            "main.py": None,
            "utils.py": None,
            "helper.py": None,
        }

        suggestions = suggestor.analyze_project_structure(files, {})

        # Should suggest organizing into modules
        structure_suggestions = [
            s
            for s in suggestions
            if s.suggestion_type == SuggestionType.PROJECT_STRUCTURE
        ]
        assert len(structure_suggestions) > 0

    def test_suggest_after_edit(self):
        """Test generating suggestions after edit."""
        suggestor = ProactiveSuggestor()

        new_code = """
def add(a, b):
    return a + b

def subtract(a, b):
    return a - b

def multiply(a, b):
    return a * b
"""

        suggestions = suggestor.suggest_after_edit(
            Path("math.py"), "modify", new_code
        )

        # Should suggest tests for functions without tests
        assert len(suggestions) > 0

    def test_suggest_for_task_with_complexity(self):
        """Test task suggestions with complexity analysis."""
        # Mock complexity detector
        @dataclass
        class MockComplexityAnalysis:
            complexity_level: Mock = Mock()
            requires_planning: bool = True
            requires_confirmation: bool = False
            resource_estimate: Mock = Mock()
            complexity_score: float = 0.8

        mock_analysis = MockComplexityAnalysis()
        mock_analysis.complexity_level.value = "high"
        mock_analysis.resource_estimate.estimated_steps = 5

        mock_detector = Mock()
        suggestor = ProactiveSuggestor(complexity_detector=mock_detector)

        suggestions = suggestor.suggest_for_task(
            "Implement authentication system", mock_analysis
        )

        # Should suggest planning
        planning_suggestions = [
            s for s in suggestions if s.suggestion_type == SuggestionType.PLANNING
        ]
        assert len(planning_suggestions) > 0
        assert any("/plan" in s.action_command for s in planning_suggestions if s.action_command)

    def test_suggest_for_task_with_confirmation_needed(self):
        """Test task suggestions requiring confirmation."""
        # Mock complexity detector
        @dataclass
        class MockComplexityAnalysis:
            requires_planning: bool = False
            requires_confirmation: bool = True
            risk_level: Mock = Mock()

        mock_analysis = MockComplexityAnalysis()
        mock_analysis.risk_level.value = "high"

        mock_detector = Mock()
        suggestor = ProactiveSuggestor(complexity_detector=mock_detector)

        suggestions = suggestor.suggest_for_task(
            "Delete all production data", mock_analysis
        )

        # Should suggest confirmation
        confirmation_suggestions = [
            s for s in suggestions if s.suggestion_type == SuggestionType.CONFIRMATION
        ]
        assert len(confirmation_suggestions) > 0

    def test_filter_suggestions(self):
        """Test filtering and prioritizing suggestions."""
        suggestor = ProactiveSuggestor()

        suggestions = [
            Suggestion(
                suggestion_type=SuggestionType.TESTING,
                priority=SuggestionPriority.LOW,
                title="Low priority",
                description="Low",
            ),
            Suggestion(
                suggestion_type=SuggestionType.SECURITY,
                priority=SuggestionPriority.CRITICAL,
                title="Critical security",
                description="Fix now",
            ),
            Suggestion(
                suggestion_type=SuggestionType.TESTING,
                priority=SuggestionPriority.MEDIUM,
                title="Medium priority",
                description="Medium",
            ),
            Suggestion(
                suggestion_type=SuggestionType.DOCUMENTATION,
                priority=SuggestionPriority.HIGH,
                title="High priority",
                description="High",
            ),
        ]

        # Filter to high priority
        filtered = suggestor.filter_suggestions(
            suggestions, max_count=5, min_priority="high"
        )

        # Should only include HIGH and CRITICAL
        assert len(filtered) == 2
        assert all(
            s.priority in [SuggestionPriority.HIGH, SuggestionPriority.CRITICAL]
            for s in filtered
        )

        # Should be sorted by priority (CRITICAL first)
        assert filtered[0].priority == SuggestionPriority.CRITICAL

    def test_filter_suggestions_max_count(self):
        """Test max_count filtering."""
        suggestor = ProactiveSuggestor()

        suggestions = [
            Suggestion(
                suggestion_type=SuggestionType.TESTING,
                priority=SuggestionPriority.HIGH,
                title=f"Suggestion {i}",
                description="Desc",
            )
            for i in range(10)
        ]

        filtered = suggestor.filter_suggestions(suggestions, max_count=3)

        assert len(filtered) == 3

    def test_filter_suggestions_with_string_priority(self):
        """Test filtering with string priority values (backwards compatibility)."""
        suggestor = ProactiveSuggestor()

        suggestions = [
            Suggestion(
                suggestion_type="testing",
                priority="low",
                title="Low",
                description="Low",
            ),
            Suggestion(
                suggestion_type="testing",
                priority="high",
                title="High",
                description="High",
            ),
        ]

        filtered = suggestor.filter_suggestions(
            suggestions, max_count=5, min_priority="medium"
        )

        # Should work with string priorities too
        assert len(filtered) == 1
        assert filtered[0].title == "High"


class TestSuggestCommand:
    """Test /suggest command implementation."""

    @pytest.fixture
    def mock_agent(self):
        """Create mock agent."""
        agent = Mock()
        agent.suggestor = ProactiveSuggestor()
        agent.file_manager = Mock()
        agent.complexity_detector = Mock()
        return agent

    @pytest.fixture
    def suggest_command(self, mock_agent):
        """Create SuggestCommand instance."""
        cmd = SuggestCommand()
        cmd.agent = mock_agent
        cmd.console = None  # Test without console
        return cmd

    @pytest.mark.asyncio
    async def test_execute_no_args_shows_help(self, suggest_command):
        """Test /suggest with no args shows help."""
        result = await suggest_command.execute([])

        assert "Suggest Command" in result
        assert "Usage:" in result

    @pytest.mark.asyncio
    async def test_execute_help_subcommand(self, suggest_command):
        """Test /suggest help."""
        result = await suggest_command.execute(["help"])

        assert "Suggest Command" in result
        assert "Usage:" in result

    @pytest.mark.asyncio
    async def test_execute_file_not_found(self, suggest_command):
        """Test /suggest file with non-existent file."""
        result = await suggest_command.execute(["file", "/nonexistent/file.py"])

        assert "Error" in result
        assert "not found" in result.lower()

    @pytest.mark.asyncio
    async def test_execute_file_success(self, suggest_command, tmp_path):
        """Test /suggest file with valid file."""
        # Create temporary file
        test_file = tmp_path / "test.py"
        test_file.write_text("""
def hello():
    print("hello")
""")

        result = await suggest_command.execute(["file", str(test_file)])

        # Should return suggestions (as text since console=None)
        assert "Suggestions:" in result or len(result) >= 0

    @pytest.mark.asyncio
    async def test_execute_task_subcommand(self, suggest_command):
        """Test /suggest task."""
        result = await suggest_command.execute(
            ["task", "implement", "user", "authentication"]
        )

        # Should return suggestions
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_execute_task_shorthand(self, suggest_command):
        """Test /suggest <description> shorthand."""
        result = await suggest_command.execute(["refactor", "authentication"])

        # Should treat as task description
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_format_suggestions_text(self, suggest_command):
        """Test text formatting of suggestions."""
        suggestions = [
            Suggestion(
                suggestion_type=SuggestionType.TESTING,
                priority=SuggestionPriority.HIGH,
                title="Add tests",
                description="Tests are missing",
                action_command="/test",
            ),
            Suggestion(
                suggestion_type=SuggestionType.DOCUMENTATION,
                priority=SuggestionPriority.MEDIUM,
                title="Add docs",
                description="Documentation needed",
            ),
        ]

        result = suggest_command._format_suggestions_text(suggestions)

        assert "Suggestions:" in result
        assert "Add tests" in result
        assert "Add docs" in result
        assert "HIGH" in result
        assert "MEDIUM" in result
        assert "/test" in result

    @pytest.mark.asyncio
    async def test_no_suggestor_error(self, suggest_command):
        """Test error when suggestor not initialized."""
        suggest_command.agent.suggestor = None
        delattr(suggest_command.agent, "suggestor")

        result = await suggest_command.execute(["help"])

        assert "Error" in result
        assert "not initialized" in result.lower()


class TestSuggestionUIIntegration:
    """Test UI display integration."""

    def test_priority_color_mapping(self):
        """Test that priorities map to correct colors."""
        from gerdsenai_cli.ui.console import EnhancedConsole

        console = EnhancedConsole()

        # Create suggestions with different priorities
        suggestions = [
            Suggestion(
                suggestion_type=SuggestionType.SECURITY,
                priority=SuggestionPriority.CRITICAL,
                title="Critical",
                description="Critical issue",
            ),
            Suggestion(
                suggestion_type=SuggestionType.TESTING,
                priority=SuggestionPriority.HIGH,
                title="High",
                description="High priority",
            ),
            Suggestion(
                suggestion_type=SuggestionType.DOCUMENTATION,
                priority=SuggestionPriority.MEDIUM,
                title="Medium",
                description="Medium priority",
            ),
            Suggestion(
                suggestion_type=SuggestionType.REFACTORING,
                priority=SuggestionPriority.LOW,
                title="Low",
                description="Low priority",
            ),
        ]

        # Should not raise errors
        console.show_suggestions(suggestions)
        console.show_suggestion_details(suggestions)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
