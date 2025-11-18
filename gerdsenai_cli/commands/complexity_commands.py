"""
Complexity analysis commands for GerdsenAI CLI.

Provides commands to analyze task complexity and view recommendations.
"""

from .base import BaseCommand


class ComplexityCommand(BaseCommand):
    """Analyze task complexity and provide recommendations."""

    name = "complexity"
    description = "Analyze task complexity and get recommendations"
    usage = "/complexity <task_description>"

    async def execute(self, args: list[str]) -> str:
        """
        Execute the complexity command.

        Args:
            args: Command arguments

        Returns:
            Command output message
        """
        if not self.agent:
            return "Error: Agent not available"

        if not args:
            return (
                "Usage: /complexity <task_description>\n\n"
                "Examples:\n"
                "  /complexity refactor all authentication logic\n"
                "  /complexity add new database migration system\n"
                "  /complexity fix the login bug"
            )

        # Join args into task description
        task_description = " ".join(args)

        # Gather context for analysis
        context = {}

        # Add project stats if available
        if hasattr(self.agent, 'context_manager') and self.agent.context_manager.files:
            stats = self.agent.context_manager.get_project_stats()
            context['total_files'] = stats.total_files
            context['text_files'] = stats.text_files
            context['languages'] = list(stats.languages.keys())

        # Perform complexity analysis
        analysis = self.agent.complexity_detector.analyze(
            task_description,
            context=context
        )

        # Display using rich UI if available
        if self.console:
            self.console.show_complexity_analysis(analysis)
            return ""  # Already displayed via console

        # Fallback to text output
        return self._format_text_output(analysis)

    def _format_text_output(self, analysis) -> str:
        """
        Format analysis as plain text (fallback).

        Args:
            analysis: ComplexityAnalysis object

        Returns:
            Formatted text output
        """
        output = []
        output.append("\n" + "=" * 60)
        output.append("TASK COMPLEXITY ANALYSIS")
        output.append("=" * 60 + "\n")

        output.append(f"Complexity: {analysis.complexity_level.value.upper()}")
        output.append(f"Risk Level: {analysis.risk_level.value.upper()}")
        output.append(f"Score: {analysis.complexity_score:.2f}/1.0\n")

        output.append("Analysis:")
        output.append(analysis.reasoning + "\n")

        # Resource Estimate
        output.append("Resource Estimate:")
        output.append("-" * 40)
        est = analysis.resource_estimate
        hours = est.estimated_time_minutes // 60
        mins = est.estimated_time_minutes % 60
        time_str = f"{hours}h {mins}m" if hours > 0 else f"{mins}m"
        output.append(f"  Estimated Time: {time_str}")
        output.append(f"  Steps: {est.estimated_steps}")
        output.append(f"  Files Affected: {est.file_count}")
        output.append(f"  Lines of Code: ~{est.lines_of_code}")
        output.append(f"  Tests Needed: {'Yes' if est.test_coverage_needed else 'No'}")
        output.append(f"  Docs Needed: {'Yes' if est.documentation_needed else 'No'}\n")

        # Impact Assessment
        output.append("Impact Assessment:")
        output.append("-" * 40)
        impact = analysis.impact_assessment
        output.append(f"  Scope: {impact.impact_scope.value}")
        output.append(f"  Components: {', '.join(impact.affected_components)}")
        if impact.potential_side_effects:
            output.append("  Side Effects:")
            for effect in impact.potential_side_effects:
                output.append(f"    • {effect}")
        output.append(f"  Breaking Changes: {'Likely' if impact.breaking_changes_likely else 'Unlikely'}")
        output.append(f"  Migration Needed: {'Yes' if impact.requires_migration else 'No'}\n")

        # Warnings
        if analysis.warnings:
            output.append("Warnings:")
            output.append("-" * 40)
            for warning in analysis.warnings:
                output.append(f"  {warning}")
            output.append("")

        # Recommendations
        if analysis.recommendations:
            output.append("Recommendations:")
            output.append("-" * 40)
            for i, rec in enumerate(analysis.recommendations, 1):
                output.append(f"  {i}. {rec}")
            output.append("")

        # Suggestions
        if analysis.requires_planning:
            output.append("💡 Suggestion: Use multi-step planning for this task (/plan)")
        if analysis.requires_confirmation:
            output.append("🔒 Required: User confirmation needed before execution")

        output.append("\n" + "=" * 60)

        return "\n".join(output)


__all__ = ["ComplexityCommand"]
