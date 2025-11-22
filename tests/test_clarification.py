"""
Comprehensive tests for the clarification system (Phase 8d-4).

Tests the clarifying questions engine, interpretation generation,
learning from history, and integration with the agent.
"""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from gerdsenai_cli.config.settings import Settings
from gerdsenai_cli.core.clarification import (
    ClarificationEngine,
    Interpretation,
    UncertaintyType,
)


@pytest.fixture
def settings():
    """Create a settings instance for testing."""
    return Settings()


@pytest.fixture
def clarification_engine(settings):
    """Create a clarification engine for testing."""
    return ClarificationEngine(settings)


@pytest.fixture
def mock_llm_client():
    """Create a mock LLM client."""
    client = MagicMock()
    client.chat_completion = AsyncMock()
    return client


def test_should_clarify_low_confidence(clarification_engine):
    """Test that low confidence triggers clarification."""
    # Low confidence should trigger clarification
    assert clarification_engine.should_clarify(0.3, "some query")
    assert clarification_engine.should_clarify(0.5, "some query")
    assert clarification_engine.should_clarify(0.69, "some query")

    # High confidence should not trigger
    assert not clarification_engine.should_clarify(0.8, "some query")
    assert not clarification_engine.should_clarify(0.95, "some query")


def test_should_clarify_ambiguous_patterns(clarification_engine):
    """Test that ambiguous patterns trigger clarification even with high confidence."""
    # Ambiguous patterns should trigger even with high confidence
    assert clarification_engine.should_clarify(0.8, "update all files")
    assert clarification_engine.should_clarify(0.9, "fix this code")
    assert clarification_engine.should_clarify(0.85, "make everything better")
    assert clarification_engine.should_clarify(0.8, "optimize the whole project")


def test_generate_rule_based_interpretations_all_files(clarification_engine):
    """Test rule-based interpretation generation for 'all files' pattern."""
    interpretations = clarification_engine._generate_rule_based_interpretations(
        "update all files", None
    )

    assert len(interpretations) >= 2
    assert any("current directory" in i.title.lower() for i in interpretations)
    assert any("entire repository" in i.title.lower() for i in interpretations)

    # Check confidence scores are reasonable
    for interp in interpretations:
        assert 0.0 <= interp.confidence <= 1.0
        assert interp.id > 0
        assert interp.title
        assert interp.description
        assert interp.reasoning


def test_generate_rule_based_interpretations_fix_this(clarification_engine):
    """Test rule-based interpretation generation for 'fix this' pattern."""
    interpretations = clarification_engine._generate_rule_based_interpretations(
        "fix this please", None
    )

    assert len(interpretations) >= 2
    assert any("fix errors" in i.title.lower() or "bug" in i.title.lower() for i in interpretations)
    assert any("improve" in i.title.lower() or "quality" in i.title.lower() for i in interpretations)


def test_create_question(clarification_engine):
    """Test creating a clarifying question."""
    interpretations = [
        Interpretation(
            id=1,
            title="First option",
            description="First description",
            confidence=0.7,
            reasoning="Most likely",
        ),
        Interpretation(
            id=2,
            title="Second option",
            description="Second description",
            confidence=0.5,
            reasoning="Alternative",
        ),
    ]

    question = clarification_engine.create_question(
        "user input",
        interpretations,
        UncertaintyType.MULTIPLE_INTERPRETATIONS
    )

    assert question.question
    assert question.uncertainty_type == UncertaintyType.MULTIPLE_INTERPRETATIONS
    assert len(question.interpretations) == 2
    assert question.context["user_input"] == "user input"


def test_record_and_load_clarification(clarification_engine, tmp_path):
    """Test recording clarification and loading from disk."""
    # Use temporary directory for testing
    with patch.object(Path, 'home', return_value=tmp_path):
        # Create a question and record it
        interpretations = [
            Interpretation(
                id=1,
                title="Test option",
                description="Test description",
                confidence=0.8,
                reasoning="Test reasoning",
            )
        ]

        question = clarification_engine.create_question(
            "test input",
            interpretations,
            UncertaintyType.UNCLEAR_ACTION
        )

        # Record the clarification
        clarification_engine.record_clarification(
            question,
            user_choice=1,
            user_input="test input",
            was_helpful=True
        )

        assert len(clarification_engine.history) == 1

        # Create new engine and verify it loads the history
        ClarificationEngine(clarification_engine.settings)
        # History loads automatically in __init__
        # Check that file exists
        history_file = tmp_path / ".gerdsenai" / "clarification_history.json"
        assert history_file.exists()


def test_learn_from_history(clarification_engine):
    """Test learning from historical clarifications."""
    # Record a clarification
    interpretations = [
        Interpretation(
            id=1,
            title="Update current directory",
            description="Update files in current directory",
            confidence=0.6,
            reasoning="Most common",
        ),
        Interpretation(
            id=2,
            title="Update entire repository",
            description="Update all files in repository",
            confidence=0.5,
            reasoning="Alternative",
        ),
    ]

    question = clarification_engine.create_question(
        "update all files",
        interpretations,
        UncertaintyType.AMBIGUOUS_SCOPE
    )

    clarification_engine.record_clarification(
        question,
        user_choice=1,
        user_input="update all files",
        was_helpful=True
    )

    # Try similar input - should find the past interpretation
    past_interp = clarification_engine.learn_from_history("please update all files")

    assert past_interp is not None
    assert past_interp.title == "Update current directory"
    # Confidence should be boosted
    assert past_interp.confidence > 0.6


def test_similarity_check(clarification_engine):
    """Test similarity checking between texts."""
    assert clarification_engine._are_similar(
        "update all files",
        "please update all files"
    )

    assert clarification_engine._are_similar(
        "fix this code",
        "can you fix this code please"
    )

    assert not clarification_engine._are_similar(
        "update files",
        "delete everything"
    )


def test_get_stats_empty(clarification_engine):
    """Test statistics with no history."""
    stats = clarification_engine.get_stats()

    assert stats["total_clarifications"] == 0
    assert stats["helpful_rate"] == 0.0
    assert stats["most_common_type"] is None


def test_get_stats_with_history(clarification_engine):
    """Test statistics with recorded history."""
    # Record multiple clarifications
    for i in range(3):
        interpretations = [
            Interpretation(
                id=1,
                title=f"Option {i}",
                description=f"Description {i}",
                confidence=0.7,
                reasoning="Test",
            )
        ]

        question = clarification_engine.create_question(
            f"input {i}",
            interpretations,
            UncertaintyType.MULTIPLE_INTERPRETATIONS if i < 2 else UncertaintyType.AMBIGUOUS_SCOPE
        )

        clarification_engine.record_clarification(
            question,
            user_choice=1,
            user_input=f"input {i}",
            was_helpful=True
        )

    stats = clarification_engine.get_stats()

    assert stats["total_clarifications"] == 3
    assert stats["helpful_rate"] == 1.0  # All marked as helpful
    assert stats["most_common_type"] == "multiple_interpretations"
    assert "multiple_interpretations" in stats["type_breakdown"]
    assert stats["type_breakdown"]["multiple_interpretations"] == 2


@pytest.mark.asyncio
async def test_generate_llm_interpretations_success(clarification_engine, mock_llm_client):
    """Test LLM-based interpretation generation."""
    # Mock LLM response
    mock_llm_client.chat_completion.return_value = {
        "content": json.dumps({
            "interpretations": [
                {
                    "title": "LLM Option 1",
                    "description": "LLM generated description",
                    "confidence": 0.8,
                    "reasoning": "LLM reasoning",
                    "example_action": "Do something",
                    "risks": ["Some risk"]
                },
                {
                    "title": "LLM Option 2",
                    "description": "Alternative description",
                    "confidence": 0.6,
                    "reasoning": "Alternative reasoning",
                    "example_action": "Do something else",
                    "risks": []
                }
            ]
        })
    }

    clarification_engine.llm_client = mock_llm_client

    interpretations = await clarification_engine._generate_llm_interpretations(
        "ambiguous input",
        current_intent=None
    )

    assert len(interpretations) == 2
    assert interpretations[0].title == "LLM Option 1"
    assert interpretations[0].confidence == 0.8
    assert interpretations[0].risks == ["Some risk"]
    assert interpretations[1].title == "LLM Option 2"


@pytest.mark.asyncio
async def test_generate_llm_interpretations_with_markdown(clarification_engine, mock_llm_client):
    """Test LLM interpretation generation with markdown code blocks."""
    # Mock LLM response with markdown formatting
    mock_llm_client.chat_completion.return_value = {
        "content": "```json\n" + json.dumps({
            "interpretations": [
                {
                    "title": "Test Option",
                    "description": "Test description",
                    "confidence": 0.7,
                    "reasoning": "Test",
                    "example_action": "Test action",
                    "risks": []
                }
            ]
        }) + "\n```"
    }

    clarification_engine.llm_client = mock_llm_client

    interpretations = await clarification_engine._generate_llm_interpretations(
        "test input",
        current_intent=None
    )

    assert len(interpretations) == 1
    assert interpretations[0].title == "Test Option"


@pytest.mark.asyncio
async def test_generate_llm_interpretations_failure_fallback(clarification_engine, mock_llm_client):
    """Test fallback to empty list when LLM fails."""
    # Mock LLM to raise an exception
    mock_llm_client.chat_completion.side_effect = Exception("LLM error")

    clarification_engine.llm_client = mock_llm_client

    interpretations = await clarification_engine._generate_llm_interpretations(
        "test input",
        current_intent=None
    )

    # Should return empty list on failure
    assert interpretations == []


@pytest.mark.asyncio
async def test_generate_interpretations_prefers_llm(clarification_engine, mock_llm_client):
    """Test that generate_interpretations prefers LLM over rule-based."""
    # Mock successful LLM response
    mock_llm_client.chat_completion.return_value = {
        "content": json.dumps({
            "interpretations": [
                {
                    "title": "LLM Option",
                    "description": "From LLM",
                    "confidence": 0.8,
                    "reasoning": "LLM",
                    "example_action": "LLM action",
                    "risks": []
                }
            ]
        })
    }

    clarification_engine.llm_client = mock_llm_client

    interpretations = await clarification_engine.generate_interpretations(
        "update all files",
        current_intent=None
    )

    # Should use LLM interpretations
    assert len(interpretations) > 0
    assert interpretations[0].title == "LLM Option"


@pytest.mark.asyncio
async def test_generate_interpretations_falls_back_to_rules(clarification_engine, mock_llm_client):
    """Test fallback to rule-based when LLM fails."""
    # Mock LLM failure
    mock_llm_client.chat_completion.side_effect = Exception("LLM error")

    clarification_engine.llm_client = mock_llm_client

    interpretations = await clarification_engine.generate_interpretations(
        "update all files",
        current_intent=None
    )

    # Should fall back to rule-based interpretations
    assert len(interpretations) > 0
    # Rule-based should generate interpretations for "all files" pattern
    assert any("current directory" in i.title.lower() or "repository" in i.title.lower()
               for i in interpretations)


def test_confidence_threshold_configurable(settings):
    """Test that confidence threshold is configurable."""
    # Set custom threshold in settings
    settings.set_preference("clarification_confidence_threshold", 0.6)

    engine = ClarificationEngine(settings)

    assert engine.confidence_threshold == 0.6

    # Test should_clarify with custom threshold
    assert engine.should_clarify(0.5, "query")  # Below 0.6
    assert not engine.should_clarify(0.7, "query")  # Above 0.6


def test_history_persistence_format(clarification_engine, tmp_path):
    """Test that history is saved in correct JSON format."""
    with patch.object(Path, 'home', return_value=tmp_path):
        # Record a clarification
        interpretations = [
            Interpretation(
                id=1,
                title="Test",
                description="Test desc",
                confidence=0.8,
                reasoning="Test reason",
                example_action="Test action",
                risks=["Risk 1"]
            )
        ]

        question = clarification_engine.create_question(
            "test",
            interpretations,
            UncertaintyType.UNCLEAR_ACTION
        )

        clarification_engine.record_clarification(
            question, 1, "test", was_helpful=True
        )

        # Check JSON file format
        history_file = tmp_path / ".gerdsenai" / "clarification_history.json"
        assert history_file.exists()

        with open(history_file) as f:
            data = json.load(f)

        assert "history" in data
        assert len(data["history"]) == 1

        record = data["history"][0]
        assert record["user_choice"] == 1
        assert record["user_input"] == "test"
        assert record["was_helpful"] is True
        assert "question" in record
        assert record["question"]["uncertainty_type"] == "unclear_action"


def test_history_limit(clarification_engine, tmp_path):
    """Test that history is limited to 100 records."""
    with patch.object(Path, 'home', return_value=tmp_path):
        # Record 150 clarifications
        for i in range(150):
            interpretations = [
                Interpretation(
                    id=1,
                    title=f"Test {i}",
                    description="Test",
                    confidence=0.7,
                    reasoning="Test"
                )
            ]

            question = clarification_engine.create_question(
                f"test {i}",
                interpretations,
                UncertaintyType.MULTIPLE_INTERPRETATIONS
            )

            clarification_engine.record_clarification(
                question, 1, f"test {i}", was_helpful=True
            )

        # Check that only last 100 are saved
        history_file = tmp_path / ".gerdsenai" / "clarification_history.json"
        with open(history_file) as f:
            data = json.load(f)

        assert len(data["history"]) == 100
        # Should contain most recent records
        assert data["history"][-1]["user_input"] == "test 149"


def test_uncertainty_types_enum():
    """Test that all uncertainty types are properly defined."""
    # Check all expected types exist
    expected_types = [
        "AMBIGUOUS_SCOPE",
        "UNCLEAR_ACTION",
        "MULTIPLE_INTERPRETATIONS",
        "MISSING_CONTEXT",
        "CONFLICTING_INTENT",
        "RISKY_OPERATION"
    ]

    for type_name in expected_types:
        assert hasattr(UncertaintyType, type_name)
        uncertainty = getattr(UncertaintyType, type_name)
        assert isinstance(uncertainty, UncertaintyType)


def test_interpretation_dataclass():
    """Test Interpretation dataclass creation and defaults."""
    # Test with all fields
    interp = Interpretation(
        id=1,
        title="Test",
        description="Test desc",
        confidence=0.8,
        reasoning="Because",
        example_action="Do this",
        risks=["Risk 1", "Risk 2"]
    )

    assert interp.id == 1
    assert interp.title == "Test"
    assert interp.confidence == 0.8
    assert len(interp.risks) == 2

    # Test with minimal fields (defaults)
    min_interp = Interpretation(
        id=2,
        title="Min",
        description="Min desc",
        confidence=0.5,
        reasoning="Min reason"
    )

    assert min_interp.example_action is None
    assert min_interp.risks == []
