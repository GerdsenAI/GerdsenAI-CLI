"""
Complexity Detection System for GerdsenAI CLI.

This module implements sophisticated task complexity analysis using multi-dimensional
factors, predictive modeling, impact assessment, and risk classification.
"""

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class ComplexityLevel(Enum):
    """Overall complexity classification."""

    TRIVIAL = "trivial"  # <5 min, single step, no risk
    SIMPLE = "simple"  # 5-15 min, few steps, low risk
    MODERATE = "moderate"  # 15-45 min, multiple steps, moderate risk
    COMPLEX = "complex"  # 1-3 hours, many steps, higher risk
    VERY_COMPLEX = "very_complex"  # 3+ hours, extensive steps, significant risk


class RiskLevel(Enum):
    """Risk classification for tasks."""

    MINIMAL = "minimal"  # Read-only, no changes
    LOW = "low"  # Minor changes, easily reversible
    MEDIUM = "medium"  # Significant changes, some impact
    HIGH = "high"  # Major changes, wide impact
    CRITICAL = "critical"  # Destructive or irreversible operations


class ImpactScope(Enum):
    """Scope of impact for task."""

    SINGLE_FILE = "single_file"  # Affects one file
    FEW_FILES = "few_files"  # Affects 2-5 files
    MODULE = "module"  # Affects a module/directory
    SUBSYSTEM = "subsystem"  # Affects multiple modules
    WHOLE_SYSTEM = "whole_system"  # Affects entire codebase


@dataclass
class ComplexityFactors:
    """Individual factors contributing to complexity."""

    # Scope factors (0.0 - 1.0)
    scope_breadth: float = 0.0  # How many files/components affected
    scope_depth: float = 0.0  # How deep into architecture

    # Technical factors
    technical_difficulty: float = 0.0  # Inherent technical complexity
    dependency_complexity: float = 0.0  # Number and complexity of dependencies
    cross_cutting_concerns: float = 0.0  # Affects multiple layers/concerns

    # Change factors
    modification_extent: float = 0.0  # How much code needs changing
    refactoring_needed: float = 0.0  # Extent of refactoring required
    testing_complexity: float = 0.0  # How hard to test changes

    # Risk factors
    reversibility: float = (
        1.0  # How easily can changes be undone (1.0 = fully reversible)
    )
    data_impact: float = 0.0  # Potential data loss/corruption risk
    breaking_changes: float = 0.0  # Likelihood of breaking existing functionality

    # Uncertainty factors
    ambiguity: float = 0.0  # How unclear the requirements are
    unknowns: float = 0.0  # Number of unknown factors

    def get_weighted_score(self) -> float:
        """
        Calculate weighted complexity score.

        Returns:
            Overall complexity score (0.0 to 1.0)
        """
        # Weight different factor categories
        scope_score = (self.scope_breadth * 0.6 + self.scope_depth * 0.4) * 0.25
        technical_score = (
            self.technical_difficulty * 0.5
            + self.dependency_complexity * 0.3
            + self.cross_cutting_concerns * 0.2
        ) * 0.25
        change_score = (
            self.modification_extent * 0.4
            + self.refactoring_needed * 0.4
            + self.testing_complexity * 0.2
        ) * 0.20
        risk_score = (
            (1.0 - self.reversibility) * 0.3
            + self.data_impact * 0.4
            + self.breaking_changes * 0.3
        ) * 0.20
        uncertainty_score = (self.ambiguity * 0.5 + self.unknowns * 0.5) * 0.10

        return (
            scope_score
            + technical_score
            + change_score
            + risk_score
            + uncertainty_score
        )


@dataclass
class ResourceEstimate:
    """Estimated resources needed for task."""

    estimated_time_minutes: int  # Estimated time in minutes
    estimated_steps: int  # Number of distinct steps
    file_count: int  # Number of files to modify
    lines_of_code: int  # Approximate LOC to modify
    test_coverage_needed: bool = True  # Whether tests are needed
    documentation_needed: bool = True  # Whether docs should be updated


@dataclass
class ImpactAssessment:
    """Assessment of task impact on codebase."""

    impact_scope: ImpactScope
    affected_components: list[str]  # List of affected components
    affected_files: list[str]  # Estimated files to change
    potential_side_effects: list[str]  # Possible unintended consequences
    breaking_changes_likely: bool = False
    requires_migration: bool = False


@dataclass
class ComplexityAnalysis:
    """Complete complexity analysis result."""

    user_input: str
    complexity_level: ComplexityLevel
    complexity_score: float  # 0.0 to 1.0
    risk_level: RiskLevel
    factors: ComplexityFactors
    resource_estimate: ResourceEstimate
    impact_assessment: ImpactAssessment
    reasoning: str  # Explanation of complexity assessment
    recommendations: list[str]  # Suggested approaches
    warnings: list[str] = field(default_factory=list)  # Warnings about the task
    requires_planning: bool = False  # Whether multi-step planning recommended
    requires_confirmation: bool = False  # Whether user confirmation needed
    analyzed_at: str = field(default_factory=lambda: datetime.now().isoformat())


class ComplexityDetector:
    """Detects and analyzes task complexity using multiple factors."""

    def __init__(self, llm_client=None):
        """
        Initialize complexity detector.

        Args:
            llm_client: Optional LLM client for advanced analysis
        """
        self.llm_client = llm_client

        # Pattern-based complexity indicators
        self.high_complexity_patterns = [
            r"\ball\b.*\bfiles\b",
            r"\bevery\b.*\bfile\b",
            r"\bentire\b.*\b(project|codebase|repository)\b",
            r"\brefactor\b.*\ball\b",
            r"\bmigrate\b",
            r"\brewrite\b",
            r"\brestructure\b",
            r"\barchitecture\b",
        ]

        self.moderate_complexity_patterns = [
            r"\bmultiple\b.*\bfiles\b",
            r"\brefactor\b",
            r"\breorganize\b",
            r"\bimplement\b.*\bfeature\b",
            r"\badd\b.*\bsystem\b",
            r"\bintegrate\b",
        ]

        self.destructive_patterns = [
            r"\bdelete\b.*\ball\b",
            r"\bremove\b.*\beverything\b",
            r"\bdrop\b.*\b(database|table|data)\b",
            r"\btruncate\b",
            r"\bpurge\b",
        ]

        self.multi_step_keywords = [
            "refactor",
            "implement",
            "migrate",
            "integrate",
            "deploy",
            "configure",
            "setup",
        ]

    def analyze(
        self, user_input: str, context: dict[str, Any] | None = None
    ) -> ComplexityAnalysis:
        """
        Analyze task complexity.

        Args:
            user_input: User's task description
            context: Optional context (project info, current files, etc.)

        Returns:
            Complete complexity analysis
        """
        context = context or {}

        # Analyze complexity factors
        factors = self._analyze_factors(user_input, context)

        # Calculate overall complexity
        complexity_score = factors.get_weighted_score()
        complexity_level = self._classify_complexity(complexity_score)

        # Assess risk
        risk_level = self._assess_risk(factors, user_input)

        # Estimate resources
        resource_estimate = self._estimate_resources(factors, complexity_level, context)

        # Assess impact
        impact_assessment = self._assess_impact(user_input, factors, context)

        # Generate reasoning
        reasoning = self._generate_reasoning(
            factors, complexity_level, risk_level, user_input
        )

        # Generate recommendations
        recommendations = self._generate_recommendations(
            complexity_level, risk_level, factors
        )

        # Generate warnings
        warnings = self._generate_warnings(risk_level, factors, user_input)

        # Determine if planning/confirmation needed
        requires_planning = complexity_level in [
            ComplexityLevel.COMPLEX,
            ComplexityLevel.VERY_COMPLEX,
        ]
        requires_confirmation = risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]

        return ComplexityAnalysis(
            user_input=user_input,
            complexity_level=complexity_level,
            complexity_score=complexity_score,
            risk_level=risk_level,
            factors=factors,
            resource_estimate=resource_estimate,
            impact_assessment=impact_assessment,
            reasoning=reasoning,
            recommendations=recommendations,
            warnings=warnings,
            requires_planning=requires_planning,
            requires_confirmation=requires_confirmation,
        )

    def _analyze_factors(
        self, user_input: str, context: dict[str, Any]
    ) -> ComplexityFactors:
        """
        Analyze individual complexity factors.

        Args:
            user_input: User's task description
            context: Context information

        Returns:
            Complexity factors
        """
        factors = ComplexityFactors()

        input_lower = user_input.lower()

        # Scope factors
        if any(re.search(p, input_lower) for p in self.high_complexity_patterns):
            factors.scope_breadth = 0.9
            factors.scope_depth = 0.7
        elif any(re.search(p, input_lower) for p in self.moderate_complexity_patterns):
            factors.scope_breadth = 0.6
            factors.scope_depth = 0.5
        elif "multiple" in input_lower or "several" in input_lower:
            factors.scope_breadth = 0.4
            factors.scope_depth = 0.3
        else:
            factors.scope_breadth = 0.2
            factors.scope_depth = 0.2

        # Technical difficulty
        if any(
            kw in input_lower for kw in ["architecture", "design pattern", "algorithm"]
        ):
            factors.technical_difficulty = 0.8
        elif any(kw in input_lower for kw in ["refactor", "optimize", "performance"]):
            factors.technical_difficulty = 0.6
        elif any(kw in input_lower for kw in ["implement", "add feature"]):
            factors.technical_difficulty = 0.5
        else:
            factors.technical_difficulty = 0.3

        # Dependency complexity
        if any(kw in input_lower for kw in ["integrate", "connect", "dependency"]):
            factors.dependency_complexity = 0.7
        elif "module" in input_lower or "package" in input_lower:
            factors.dependency_complexity = 0.5
        else:
            factors.dependency_complexity = 0.2

        # Cross-cutting concerns
        if any(
            kw in input_lower
            for kw in ["logging", "error handling", "authentication", "authorization"]
        ):
            factors.cross_cutting_concerns = 0.8
        elif any(kw in input_lower for kw in ["validation", "caching", "monitoring"]):
            factors.cross_cutting_concerns = 0.5
        else:
            factors.cross_cutting_concerns = 0.2

        # Modification extent
        if "rewrite" in input_lower or "complete" in input_lower:
            factors.modification_extent = 0.9
        elif "refactor" in input_lower or "restructure" in input_lower:
            factors.modification_extent = 0.7
        elif "update" in input_lower or "modify" in input_lower:
            factors.modification_extent = 0.5
        else:
            factors.modification_extent = 0.3

        # Refactoring needed
        if "refactor" in input_lower:
            factors.refactoring_needed = 0.8
        elif any(kw in input_lower for kw in ["restructure", "reorganize", "clean up"]):
            factors.refactoring_needed = 0.6
        else:
            factors.refactoring_needed = 0.2

        # Testing complexity
        if factors.scope_breadth > 0.7 or factors.technical_difficulty > 0.7:
            factors.testing_complexity = 0.8
        elif factors.scope_breadth > 0.5:
            factors.testing_complexity = 0.5
        else:
            factors.testing_complexity = 0.3

        # Reversibility (inverse - lower is worse)
        if any(re.search(p, input_lower) for p in self.destructive_patterns):
            factors.reversibility = 0.1  # Mostly irreversible
        elif "delete" in input_lower or "remove" in input_lower:
            factors.reversibility = 0.5  # Partially reversible
        else:
            factors.reversibility = 0.9  # Mostly reversible

        # Data impact
        if any(kw in input_lower for kw in ["database", "data", "migration", "schema"]):
            factors.data_impact = 0.7
        elif "file" in input_lower and (
            "delete" in input_lower or "remove" in input_lower
        ):
            factors.data_impact = 0.5
        else:
            factors.data_impact = 0.1

        # Breaking changes likelihood
        if any(
            kw in input_lower for kw in ["breaking", "incompatible", "major version"]
        ):
            factors.breaking_changes = 0.9
        elif "api" in input_lower or "interface" in input_lower:
            factors.breaking_changes = 0.6
        elif factors.scope_breadth > 0.7:
            factors.breaking_changes = 0.5
        else:
            factors.breaking_changes = 0.2

        # Ambiguity
        vague_words = ["fix", "improve", "better", "optimize", "clean"]
        ambiguity_count = sum(1 for word in vague_words if word in input_lower)
        factors.ambiguity = min(0.9, ambiguity_count * 0.3)

        # Unknowns
        question_words = ["how", "what", "where", "which", "should"]
        unknown_count = sum(1 for word in question_words if word in input_lower)
        factors.unknowns = min(0.8, unknown_count * 0.3)

        return factors

    def _classify_complexity(self, score: float) -> ComplexityLevel:
        """
        Classify overall complexity level.

        Args:
            score: Weighted complexity score

        Returns:
            Complexity level classification
        """
        if score < 0.2:
            return ComplexityLevel.TRIVIAL
        elif score < 0.4:
            return ComplexityLevel.SIMPLE
        elif score < 0.6:
            return ComplexityLevel.MODERATE
        elif score < 0.8:
            return ComplexityLevel.COMPLEX
        else:
            return ComplexityLevel.VERY_COMPLEX

    def _assess_risk(self, factors: ComplexityFactors, user_input: str) -> RiskLevel:
        """
        Assess risk level of task.

        Args:
            factors: Complexity factors
            user_input: User's input

        Returns:
            Risk level classification
        """
        # Calculate risk score
        risk_score = (
            (1.0 - factors.reversibility) * 0.4
            + factors.data_impact * 0.3
            + factors.breaking_changes * 0.2
            + factors.scope_breadth * 0.1
        )

        # Check for destructive patterns
        if any(re.search(p, user_input.lower()) for p in self.destructive_patterns):
            return RiskLevel.CRITICAL

        if risk_score < 0.2:
            return RiskLevel.MINIMAL
        elif risk_score < 0.4:
            return RiskLevel.LOW
        elif risk_score < 0.6:
            return RiskLevel.MEDIUM
        elif risk_score < 0.8:
            return RiskLevel.HIGH
        else:
            return RiskLevel.CRITICAL

    def _estimate_resources(
        self,
        factors: ComplexityFactors,
        complexity_level: ComplexityLevel,
        context: dict[str, Any],
    ) -> ResourceEstimate:
        """
        Estimate resources needed for task.

        Args:
            factors: Complexity factors
            complexity_level: Overall complexity
            context: Context information

        Returns:
            Resource estimate
        """
        # Estimate time based on complexity
        time_map = {
            ComplexityLevel.TRIVIAL: (1, 5),
            ComplexityLevel.SIMPLE: (5, 15),
            ComplexityLevel.MODERATE: (15, 45),
            ComplexityLevel.COMPLEX: (60, 180),
            ComplexityLevel.VERY_COMPLEX: (180, 480),
        }

        min_time, max_time = time_map[complexity_level]
        # Use midpoint with factor adjustment
        estimated_time = int((min_time + max_time) / 2 * (1 + factors.ambiguity * 0.5))

        # Estimate steps
        steps_map = {
            ComplexityLevel.TRIVIAL: 1,
            ComplexityLevel.SIMPLE: 2,
            ComplexityLevel.MODERATE: 4,
            ComplexityLevel.COMPLEX: 8,
            ComplexityLevel.VERY_COMPLEX: 15,
        }

        estimated_steps = steps_map[complexity_level]

        # Estimate file count
        if factors.scope_breadth > 0.8:
            file_count = 20
        elif factors.scope_breadth > 0.6:
            file_count = 10
        elif factors.scope_breadth > 0.4:
            file_count = 5
        else:
            file_count = 1

        # Estimate lines of code
        lines_of_code = int(file_count * 100 * (1 + factors.modification_extent))

        # Determine if tests and docs needed
        test_coverage_needed = complexity_level in [
            ComplexityLevel.MODERATE,
            ComplexityLevel.COMPLEX,
            ComplexityLevel.VERY_COMPLEX,
        ]

        documentation_needed = complexity_level in [
            ComplexityLevel.COMPLEX,
            ComplexityLevel.VERY_COMPLEX,
        ]

        return ResourceEstimate(
            estimated_time_minutes=estimated_time,
            estimated_steps=estimated_steps,
            file_count=file_count,
            lines_of_code=lines_of_code,
            test_coverage_needed=test_coverage_needed,
            documentation_needed=documentation_needed,
        )

    def _assess_impact(
        self, user_input: str, factors: ComplexityFactors, context: dict[str, Any]
    ) -> ImpactAssessment:
        """
        Assess impact on codebase.

        Args:
            user_input: User's input
            factors: Complexity factors
            context: Context information

        Returns:
            Impact assessment
        """
        # Determine impact scope
        if factors.scope_breadth > 0.8:
            impact_scope = ImpactScope.WHOLE_SYSTEM
        elif factors.scope_breadth > 0.6:
            impact_scope = ImpactScope.SUBSYSTEM
        elif factors.scope_breadth > 0.4:
            impact_scope = ImpactScope.MODULE
        elif factors.scope_breadth > 0.2:
            impact_scope = ImpactScope.FEW_FILES
        else:
            impact_scope = ImpactScope.SINGLE_FILE

        # Extract potential components from input
        affected_components = []
        input_lower = user_input.lower()

        component_keywords = {
            "authentication": ["auth", "login", "session", "token"],
            "database": ["database", "db", "sql", "query", "schema"],
            "api": ["api", "endpoint", "route", "controller"],
            "ui": ["ui", "interface", "component", "view", "template"],
            "testing": ["test", "spec", "unit test", "integration test"],
            "configuration": ["config", "settings", "environment"],
        }

        for component, keywords in component_keywords.items():
            if any(kw in input_lower for kw in keywords):
                affected_components.append(component)

        # Estimate affected files
        affected_files = []  # Would be populated with actual file analysis

        # Identify potential side effects
        potential_side_effects = []

        if factors.dependency_complexity > 0.6:
            potential_side_effects.append("May affect dependent modules")

        if factors.breaking_changes > 0.5:
            potential_side_effects.append("May break existing functionality")

        if factors.cross_cutting_concerns > 0.6:
            potential_side_effects.append("Changes affect multiple system layers")

        if factors.data_impact > 0.5:
            potential_side_effects.append("May affect data integrity")

        # Determine if breaking changes likely
        breaking_changes_likely = factors.breaking_changes > 0.6

        # Determine if migration needed
        requires_migration = any(
            kw in input_lower for kw in ["migrate", "migration", "upgrade", "version"]
        )

        return ImpactAssessment(
            impact_scope=impact_scope,
            affected_components=affected_components or ["general"],
            affected_files=affected_files,
            potential_side_effects=potential_side_effects,
            breaking_changes_likely=breaking_changes_likely,
            requires_migration=requires_migration,
        )

    def _generate_reasoning(
        self,
        factors: ComplexityFactors,
        complexity_level: ComplexityLevel,
        risk_level: RiskLevel,
        user_input: str,
    ) -> str:
        """
        Generate human-readable reasoning for complexity assessment.

        Args:
            factors: Complexity factors
            complexity_level: Assessed complexity level
            risk_level: Assessed risk level
            user_input: User's input

        Returns:
            Reasoning explanation
        """
        reasoning_parts = []

        # Overall assessment
        reasoning_parts.append(
            f"This task is classified as {complexity_level.value.upper()} "
            f"with {risk_level.value.upper()} risk."
        )

        # Scope reasoning
        if factors.scope_breadth > 0.6:
            reasoning_parts.append(
                f"The task has broad scope affecting multiple files/components "
                f"(scope: {factors.scope_breadth:.0%})."
            )

        # Technical reasoning
        if factors.technical_difficulty > 0.6:
            reasoning_parts.append(
                f"Technical complexity is significant "
                f"(difficulty: {factors.technical_difficulty:.0%})."
            )

        # Risk reasoning
        if factors.reversibility < 0.5:
            reasoning_parts.append(
                f"Changes may be difficult to reverse "
                f"(reversibility: {factors.reversibility:.0%})."
            )

        if factors.data_impact > 0.5:
            reasoning_parts.append(
                f"There is potential data impact/risk "
                f"(data risk: {factors.data_impact:.0%})."
            )

        # Uncertainty reasoning
        if factors.ambiguity > 0.4:
            reasoning_parts.append(
                f"Requirements have some ambiguity "
                f"(ambiguity: {factors.ambiguity:.0%})."
            )

        return " ".join(reasoning_parts)

    def _generate_recommendations(
        self,
        complexity_level: ComplexityLevel,
        risk_level: RiskLevel,
        factors: ComplexityFactors,
    ) -> list[str]:
        """
        Generate recommendations for approaching the task.

        Args:
            complexity_level: Assessed complexity
            risk_level: Assessed risk
            factors: Complexity factors

        Returns:
            List of recommendations
        """
        recommendations = []

        # Planning recommendations
        if complexity_level in [ComplexityLevel.COMPLEX, ComplexityLevel.VERY_COMPLEX]:
            recommendations.append(
                "Use multi-step planning mode to break down the task"
            )
            recommendations.append("Review the plan before execution")

        # Testing recommendations
        if factors.testing_complexity > 0.5:
            recommendations.append("Create comprehensive tests before making changes")
            recommendations.append("Run existing test suite to ensure no regressions")

        # Risk mitigation
        if risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
            recommendations.append("Create backup before making changes")
            recommendations.append("Consider implementing changes incrementally")

        if factors.reversibility < 0.5:
            recommendations.append("Ensure version control is set up (git)")
            recommendations.append("Consider creating a feature branch")

        # Documentation
        if complexity_level in [ComplexityLevel.COMPLEX, ComplexityLevel.VERY_COMPLEX]:
            recommendations.append("Document design decisions and changes")

        # Clarification
        if factors.ambiguity > 0.5:
            recommendations.append("Clarify requirements before implementation")

        if not recommendations:
            recommendations.append("Proceed with standard development workflow")

        return recommendations

    def _generate_warnings(
        self, risk_level: RiskLevel, factors: ComplexityFactors, user_input: str
    ) -> list[str]:
        """
        Generate warnings about potential issues.

        Args:
            risk_level: Assessed risk level
            factors: Complexity factors
            user_input: User's input

        Returns:
            List of warnings
        """
        warnings = []

        # Critical risk warning
        if risk_level == RiskLevel.CRITICAL:
            warnings.append(
                "⚠️  CRITICAL: This operation may be destructive and irreversible"
            )

        # High risk warning
        if risk_level == RiskLevel.HIGH:
            warnings.append("⚠️  HIGH RISK: This operation may have significant impact")

        # Data warnings
        if factors.data_impact > 0.6:
            warnings.append("⚠️  Data may be affected - ensure backups exist")

        # Breaking changes
        if factors.breaking_changes > 0.6:
            warnings.append(
                "⚠️  Breaking changes likely - API consumers may be affected"
            )

        # Low reversibility
        if factors.reversibility < 0.3:
            warnings.append("⚠️  Changes may be difficult or impossible to reverse")

        # Wide scope
        if factors.scope_breadth > 0.8:
            warnings.append("⚠️  Wide scope - many files will be affected")

        return warnings
