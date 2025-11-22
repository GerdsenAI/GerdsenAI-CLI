"""
Clarifying Questions System for GerdsenAI CLI.

This module implements intelligent clarification when the agent encounters
ambiguous or uncertain user requests. Instead of guessing, the system
asks targeted questions to understand user intent better.
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from ..config.settings import Settings

logger = logging.getLogger(__name__)


class UncertaintyType(Enum):
    """Types of uncertainty the agent can encounter."""

    AMBIGUOUS_SCOPE = "ambiguous_scope"  # "all files" - which files?
    UNCLEAR_ACTION = "unclear_action"  # "fix this" - how?
    MULTIPLE_INTERPRETATIONS = "multiple_interpretations"  # Could mean several things
    MISSING_CONTEXT = "missing_context"  # Need more info to proceed
    CONFLICTING_INTENT = "conflicting_intent"  # Request seems contradictory
    RISKY_OPERATION = "risky_operation"  # Want to confirm before destructive action


@dataclass
class Interpretation:
    """A possible interpretation of ambiguous user input."""

    id: int
    title: str
    description: str
    confidence: float  # 0.0 to 1.0
    reasoning: str
    example_action: str | None = None
    risks: list[str] = field(default_factory=list)


@dataclass
class ClarifyingQuestion:
    """A question to ask the user for clarification."""

    question: str
    uncertainty_type: UncertaintyType
    interpretations: list[Interpretation]
    context: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class ClarificationHistory:
    """Historical record of a clarification exchange."""

    question: ClarifyingQuestion
    user_choice: int  # Selected interpretation ID
    user_input: str  # Original ambiguous input
    timestamp: str
    was_helpful: bool = True


class ClarificationEngine:
    """Engine for generating and managing clarifying questions."""

    def __init__(self, settings: Settings, llm_client=None):
        """
        Initialize the clarification engine.

        Args:
            settings: Application settings
            llm_client: Optional LLM client for generating interpretations
        """
        self.settings = settings
        self.llm_client = llm_client
        self.confidence_threshold = settings.get_preference(
            "clarification_confidence_threshold", 0.7
        )
        self.history: list[ClarificationHistory] = []
        self._load_history()

    def should_clarify(self, confidence: float, user_input: str) -> bool:
        """
        Determine if clarification is needed based on confidence score.

        Args:
            confidence: Confidence score from intent detection (0.0 to 1.0)
            user_input: User's input text

        Returns:
            True if clarification should be requested
        """
        # Always clarify if below threshold
        if confidence < self.confidence_threshold:
            logger.info(
                f"Confidence {confidence:.2f} below threshold {self.confidence_threshold:.2f}, "
                "will ask for clarification"
            )
            return True

        # Check for ambiguous keywords even with higher confidence
        ambiguous_patterns = [
            "all files",
            "everything",
            "the whole",
            "fix this",
            "make it better",
            "optimize",
            "improve",
        ]

        if any(pattern in user_input.lower() for pattern in ambiguous_patterns):
            logger.info(f"Ambiguous pattern detected in: {user_input}")
            return True

        return False

    async def generate_interpretations(
        self, user_input: str, current_intent: dict[str, Any] | None = None
    ) -> list[Interpretation]:
        """
        Generate multiple possible interpretations of ambiguous input.

        Args:
            user_input: User's ambiguous input
            current_intent: Currently detected intent (if any)

        Returns:
            List of possible interpretations
        """
        interpretations = []

        # Use LLM to generate interpretations if available
        if self.llm_client:
            interpretations = await self._generate_llm_interpretations(
                user_input, current_intent
            )

        # Fallback to rule-based interpretations
        if not interpretations:
            interpretations = self._generate_rule_based_interpretations(
                user_input, current_intent
            )

        # Sort by confidence (highest first)
        interpretations.sort(key=lambda i: i.confidence, reverse=True)

        return interpretations

    async def _generate_llm_interpretations(
        self, user_input: str, current_intent: dict[str, Any] | None
    ) -> list[Interpretation]:
        """
        Use LLM to generate multiple interpretations.

        Args:
            user_input: User's ambiguous input
            current_intent: Currently detected intent

        Returns:
            LLM-generated interpretations
        """
        prompt = f"""You are helping clarify an ambiguous user request. Analyze this input and suggest 2-4 possible interpretations.

User input: "{user_input}"

For each interpretation, provide:
1. A clear title (5-10 words)
2. A detailed description
3. Confidence score (0.0 to 1.0)
4. Reasoning for this interpretation
5. Example of what action would be taken
6. Any risks with this interpretation

Respond with JSON only:
{{
  "interpretations": [
    {{
      "title": "...",
      "description": "...",
      "confidence": 0.8,
      "reasoning": "...",
      "example_action": "...",
      "risks": ["..."]
    }}
  ]
}}"""

        try:
            from .llm_client import ChatMessage

            messages = [ChatMessage(role="user", content=prompt)]

            response = await self.llm_client.chat_completion(
                messages=messages, max_tokens=1500, temperature=0.7
            )

            # Parse JSON response
            content = response.get("content", "")
            # Extract JSON from potential markdown code blocks
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            data = json.loads(content)

            interpretations = []
            for idx, interp_data in enumerate(data.get("interpretations", []), 1):
                interpretations.append(
                    Interpretation(
                        id=idx,
                        title=interp_data.get("title", ""),
                        description=interp_data.get("description", ""),
                        confidence=float(interp_data.get("confidence", 0.5)),
                        reasoning=interp_data.get("reasoning", ""),
                        example_action=interp_data.get("example_action"),
                        risks=interp_data.get("risks", []),
                    )
                )

            return interpretations

        except Exception as e:
            logger.warning(f"Failed to generate LLM interpretations: {e}")
            return []

    def _generate_rule_based_interpretations(
        self, user_input: str, current_intent: dict[str, Any] | None
    ) -> list[Interpretation]:
        """
        Generate interpretations using rule-based heuristics.

        Args:
            user_input: User's ambiguous input
            current_intent: Currently detected intent

        Returns:
            Rule-based interpretations
        """
        interpretations = []
        input_lower = user_input.lower()

        # Pattern: "all files" / "everything"
        if "all files" in input_lower or "everything" in input_lower:
            interpretations.extend(
                [
                    Interpretation(
                        id=1,
                        title="All files in current directory",
                        description="Operate on files in the current working directory only",
                        confidence=0.6,
                        reasoning="Most common interpretation for 'all files'",
                        example_action="Process files in ./",
                    ),
                    Interpretation(
                        id=2,
                        title="All files in entire repository",
                        description="Recursively operate on all files in the git repository",
                        confidence=0.5,
                        reasoning="Could mean entire project",
                        example_action="Process all files recursively",
                        risks=["May affect many files", "Could be time-consuming"],
                    ),
                    Interpretation(
                        id=3,
                        title="All files of specific type",
                        description="All Python files, or all test files, etc.",
                        confidence=0.4,
                        reasoning="Context might indicate specific file type",
                        example_action="Process *.py or test_*.py files",
                    ),
                ]
            )

        # Pattern: "fix this" / "improve"
        elif any(
            word in input_lower for word in ["fix this", "fix it", "improve", "better"]
        ):
            interpretations.extend(
                [
                    Interpretation(
                        id=1,
                        title="Fix errors/bugs in current context",
                        description="Identify and fix errors in recently discussed files",
                        confidence=0.7,
                        reasoning="Common request when working on specific code",
                        example_action="Analyze and fix bugs in current file",
                    ),
                    Interpretation(
                        id=2,
                        title="Improve code quality/style",
                        description="Refactor for better readability and maintainability",
                        confidence=0.5,
                        reasoning="'Improve' often means refactoring",
                        example_action="Apply refactoring patterns",
                    ),
                    Interpretation(
                        id=3,
                        title="Optimize performance",
                        description="Make code run faster or use less memory",
                        confidence=0.4,
                        reasoning="Could be asking for optimization",
                        example_action="Profile and optimize hot paths",
                    ),
                ]
            )

        # Pattern: "update" / "change"
        elif "update" in input_lower or "change" in input_lower:
            interpretations.extend(
                [
                    Interpretation(
                        id=1,
                        title="Update recently discussed files",
                        description="Modify files mentioned in recent conversation",
                        confidence=0.6,
                        reasoning="Likely referring to context",
                        example_action="Update files from conversation history",
                    ),
                    Interpretation(
                        id=2,
                        title="Update all related files",
                        description="Update files with similar patterns or dependencies",
                        confidence=0.5,
                        reasoning="Could be broader scope change",
                        example_action="Find and update related files",
                    ),
                ]
            )

        # Fallback: Generic uncertainty
        if not interpretations:
            interpretations.append(
                Interpretation(
                    id=1,
                    title="Need more information",
                    description="Request is unclear and needs additional context",
                    confidence=0.3,
                    reasoning="Unable to determine specific intent",
                    example_action="Ask for more details",
                )
            )

        return interpretations

    def create_question(
        self,
        user_input: str,
        interpretations: list[Interpretation],
        uncertainty_type: UncertaintyType = UncertaintyType.MULTIPLE_INTERPRETATIONS,
    ) -> ClarifyingQuestion:
        """
        Create a clarifying question for the user.

        Args:
            user_input: User's original input
            interpretations: Possible interpretations
            uncertainty_type: Type of uncertainty

        Returns:
            Clarifying question object
        """
        # Generate appropriate question based on uncertainty type
        if uncertainty_type == UncertaintyType.AMBIGUOUS_SCOPE:
            question = (
                "Your request mentions a broad scope. "
                "Which interpretation matches your intent?"
            )
        elif uncertainty_type == UncertaintyType.UNCLEAR_ACTION:
            question = "I want to help, but I'm not sure exactly what action to take. Which of these would you like?"
        elif uncertainty_type == UncertaintyType.MULTIPLE_INTERPRETATIONS:
            question = (
                "I see multiple ways to interpret your request. Which one did you mean?"
            )
        else:
            question = "Could you clarify what you'd like me to do?"

        return ClarifyingQuestion(
            question=question,
            uncertainty_type=uncertainty_type,
            interpretations=interpretations,
            context={"user_input": user_input},
        )

    def record_clarification(
        self,
        question: ClarifyingQuestion,
        user_choice: int,
        user_input: str,
        was_helpful: bool = True,
    ) -> None:
        """
        Record a clarification exchange for learning.

        Args:
            question: The clarifying question that was asked
            user_choice: Which interpretation the user selected
            user_input: Original user input
            was_helpful: Whether the clarification was helpful
        """
        record = ClarificationHistory(
            question=question,
            user_choice=user_choice,
            user_input=user_input,
            timestamp=datetime.now().isoformat(),
            was_helpful=was_helpful,
        )

        self.history.append(record)
        self._save_history()

        logger.info(
            f"Recorded clarification: user chose interpretation {user_choice} "
            f"for '{user_input[:50]}...'"
        )

    def learn_from_history(self, user_input: str) -> Interpretation | None:
        """
        Check history for similar past clarifications to learn from.

        Args:
            user_input: Current user input

        Returns:
            Previously chosen interpretation if found, None otherwise
        """
        # Simple similarity check (could be enhanced with embeddings)
        input_lower = user_input.lower()

        for record in reversed(self.history):  # Most recent first
            if not record.was_helpful:
                continue

            historical_input = record.user_input.lower()

            # Check for similar patterns
            if self._are_similar(input_lower, historical_input):
                # Find the chosen interpretation
                for interp in record.question.interpretations:
                    if interp.id == record.user_choice:
                        logger.info(
                            f"Found similar past clarification, suggesting interpretation: {interp.title}"
                        )
                        # Boost confidence since user chose this before
                        interp.confidence = min(1.0, interp.confidence + 0.2)
                        return interp

        return None

    def _are_similar(self, text1: str, text2: str, threshold: float = 0.6) -> bool:
        """
        Check if two texts are similar using simple word overlap.

        Args:
            text1: First text
            text2: Second text
            threshold: Similarity threshold (0.0 to 1.0)

        Returns:
            True if texts are similar enough
        """
        words1 = set(text1.split())
        words2 = set(text2.split())

        if not words1 or not words2:
            return False

        intersection = words1.intersection(words2)
        union = words1.union(words2)

        similarity = len(intersection) / len(union)
        return similarity >= threshold

    def _load_history(self) -> None:
        """Load clarification history from disk."""
        history_file = Path.home() / ".gerdsenai" / "clarification_history.json"

        if not history_file.exists():
            return

        try:
            with open(history_file, encoding="utf-8") as f:
                data = json.load(f)

            # Reconstruct history objects
            for record_data in data.get("history", []):
                # Reconstruct interpretations
                interpretations = []
                for interp_data in record_data["question"]["interpretations"]:
                    interpretations.append(
                        Interpretation(
                            id=interp_data["id"],
                            title=interp_data["title"],
                            description=interp_data["description"],
                            confidence=interp_data["confidence"],
                            reasoning=interp_data["reasoning"],
                            example_action=interp_data.get("example_action"),
                            risks=interp_data.get("risks", []),
                        )
                    )

                # Reconstruct question
                question = ClarifyingQuestion(
                    question=record_data["question"]["question"],
                    uncertainty_type=UncertaintyType(
                        record_data["question"]["uncertainty_type"]
                    ),
                    interpretations=interpretations,
                    context=record_data["question"].get("context", {}),
                    created_at=record_data["question"].get("created_at", ""),
                )

                # Reconstruct history record
                self.history.append(
                    ClarificationHistory(
                        question=question,
                        user_choice=record_data["user_choice"],
                        user_input=record_data["user_input"],
                        timestamp=record_data["timestamp"],
                        was_helpful=record_data.get("was_helpful", True),
                    )
                )

            logger.info(f"Loaded {len(self.history)} clarification records")

        except Exception as e:
            logger.warning(f"Failed to load clarification history: {e}")

    def _save_history(self) -> None:
        """Save clarification history to disk."""
        history_file = Path.home() / ".gerdsenai" / "clarification_history.json"
        history_file.parent.mkdir(parents=True, exist_ok=True)

        try:
            # Convert to JSON-serializable format
            data = {"history": []}

            for record in self.history:
                record_data = {
                    "question": {
                        "question": record.question.question,
                        "uncertainty_type": record.question.uncertainty_type.value,
                        "interpretations": [
                            {
                                "id": interp.id,
                                "title": interp.title,
                                "description": interp.description,
                                "confidence": interp.confidence,
                                "reasoning": interp.reasoning,
                                "example_action": interp.example_action,
                                "risks": interp.risks,
                            }
                            for interp in record.question.interpretations
                        ],
                        "context": record.question.context,
                        "created_at": record.question.created_at,
                    },
                    "user_choice": record.user_choice,
                    "user_input": record.user_input,
                    "timestamp": record.timestamp,
                    "was_helpful": record.was_helpful,
                }
                data["history"].append(record_data)

            # Keep only last 100 records
            if len(data["history"]) > 100:
                data["history"] = data["history"][-100:]

            with open(history_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

            logger.debug(f"Saved {len(data['history'])} clarification records")

        except Exception as e:
            logger.warning(f"Failed to save clarification history: {e}")

    def get_stats(self) -> dict[str, Any]:
        """
        Get statistics about clarification usage.

        Returns:
            Dictionary with clarification statistics
        """
        if not self.history:
            return {
                "total_clarifications": 0,
                "helpful_rate": 0.0,
                "most_common_type": None,
            }

        helpful_count = sum(1 for r in self.history if r.was_helpful)
        type_counts: dict[str, int] = {}

        for record in self.history:
            type_name = record.question.uncertainty_type.value
            type_counts[type_name] = type_counts.get(type_name, 0) + 1

        most_common = (
            max(type_counts.items(), key=lambda x: x[1])[0] if type_counts else None
        )

        return {
            "total_clarifications": len(self.history),
            "helpful_rate": helpful_count / len(self.history) if self.history else 0.0,
            "most_common_type": most_common,
            "type_breakdown": type_counts,
        }
