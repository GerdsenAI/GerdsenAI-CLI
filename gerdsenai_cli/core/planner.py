"""
Multi-step task planning system for GerdsenAI CLI.

Breaks complex tasks into sequential steps, shows preview, tracks progress,
and enables user confirmation before execution.
"""

import json
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class StepStatus(Enum):
    """Status of a plan step."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class PlanStep:
    """A single step in a task plan."""

    id: int
    title: str
    description: str
    estimated_tokens: int
    dependencies: list[int] = field(default_factory=list)  # Step IDs this depends on
    status: StepStatus = StepStatus.PENDING
    result: str | None = None
    error: str | None = None

    def can_execute(self, completed_steps: set[int]) -> bool:
        """Check if all dependencies are satisfied.

        Args:
            completed_steps: Set of completed step IDs

        Returns:
            True if step can be executed
        """
        return all(dep_id in completed_steps for dep_id in self.dependencies)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "estimated_tokens": self.estimated_tokens,
            "dependencies": self.dependencies,
            "status": self.status.value,
            "result": self.result,
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PlanStep":
        """Create from dictionary."""
        return cls(
            id=data["id"],
            title=data["title"],
            description=data["description"],
            estimated_tokens=data["estimated_tokens"],
            dependencies=data.get("dependencies", []),
            status=StepStatus(data.get("status", "pending")),
            result=data.get("result"),
            error=data.get("error"),
        )


@dataclass
class TaskPlan:
    """A complete multi-step plan."""

    title: str
    description: str
    steps: list[PlanStep]
    total_estimated_tokens: int
    created_at: str
    user_query: str = ""

    def get_next_step(self) -> PlanStep | None:
        """Get the next pending step with satisfied dependencies.

        Returns:
            Next executable step or None if all complete or blocked
        """
        completed_ids = {
            step.id for step in self.steps if step.status == StepStatus.COMPLETED
        }

        for step in self.steps:
            if step.status == StepStatus.PENDING and step.can_execute(completed_ids):
                return step

        return None

    def mark_step_complete(self, step_id: int, result: str) -> None:
        """Mark a step as completed.

        Args:
            step_id: ID of the step
            result: Result description
        """
        for step in self.steps:
            if step.id == step_id:
                step.status = StepStatus.COMPLETED
                step.result = result
                logger.info(f"Step {step_id} completed: {step.title}")
                break

    def mark_step_failed(self, step_id: int, error: str) -> None:
        """Mark a step as failed.

        Args:
            step_id: ID of the step
            error: Error description
        """
        for step in self.steps:
            if step.id == step_id:
                step.status = StepStatus.FAILED
                step.error = error
                logger.error(f"Step {step_id} failed: {step.title} - {error}")
                break

    def mark_step_in_progress(self, step_id: int) -> None:
        """Mark a step as in progress.

        Args:
            step_id: ID of the step
        """
        for step in self.steps:
            if step.id == step_id:
                step.status = StepStatus.IN_PROGRESS
                logger.info(f"Step {step_id} started: {step.title}")
                break

    def get_progress(self) -> tuple[int, int]:
        """Get (completed, total) steps.

        Returns:
            Tuple of (completed_count, total_count)
        """
        completed = sum(1 for step in self.steps if step.status == StepStatus.COMPLETED)
        return (completed, len(self.steps))

    def get_progress_percentage(self) -> float:
        """Get progress as percentage.

        Returns:
            Progress percentage (0.0 to 100.0)
        """
        completed, total = self.get_progress()
        return (completed / total * 100) if total > 0 else 0.0

    def is_complete(self) -> bool:
        """Check if all steps are completed.

        Returns:
            True if all steps completed
        """
        return all(step.status == StepStatus.COMPLETED for step in self.steps)

    def is_finished(self) -> bool:
        """Check if plan execution is finished (all steps processed).

        A plan is finished if all steps are in a terminal state:
        COMPLETED, SKIPPED, or FAILED.

        Returns:
            True if all steps are in a terminal state
        """
        terminal_states = {StepStatus.COMPLETED, StepStatus.SKIPPED, StepStatus.FAILED}
        return all(step.status in terminal_states for step in self.steps)

    def has_failed_steps(self) -> bool:
        """Check if any steps have failed.

        Returns:
            True if any step has failed
        """
        return any(step.status == StepStatus.FAILED for step in self.steps)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "title": self.title,
            "description": self.description,
            "steps": [step.to_dict() for step in self.steps],
            "total_estimated_tokens": self.total_estimated_tokens,
            "created_at": self.created_at,
            "user_query": self.user_query,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TaskPlan":
        """Create from dictionary."""
        return cls(
            title=data["title"],
            description=data["description"],
            steps=[PlanStep.from_dict(step_data) for step_data in data["steps"]],
            total_estimated_tokens=data["total_estimated_tokens"],
            created_at=data["created_at"],
            user_query=data.get("user_query", ""),
        )


class TaskPlanner:
    """Plans and executes multi-step tasks."""

    def __init__(self, llm_client, agent):
        """Initialize the task planner.

        Args:
            llm_client: LLM client for generating plans
            agent: Agent instance for executing steps
        """
        self.llm_client = llm_client
        self.agent = agent
        self.current_plan: TaskPlan | None = None

    async def create_plan(self, user_request: str, context: str = "") -> TaskPlan:
        """Create a plan by asking LLM to break down the task.

        Args:
            user_request: User's request
            context: Additional context about the project

        Returns:
            TaskPlan object with steps
        """
        logger.info(f"Creating plan for: {user_request}")

        # Prompt LLM to break down the task
        planning_prompt = self._build_planning_prompt(user_request, context)

        # Get plan from LLM
        plan_json = await self._get_plan_from_llm(planning_prompt)

        # Parse and create TaskPlan
        plan = self._parse_plan_response(plan_json, user_request)

        return plan

    def _build_planning_prompt(self, user_request: str, context: str = "") -> str:
        """Build prompt for LLM to generate plan.

        Args:
            user_request: User's request
            context: Project context

        Returns:
            Formatted prompt
        """
        prompt = f"""You are a task planning expert. Break down the following request into sequential, actionable steps.

User Request: {user_request}

Project Context:
{context if context else "No additional context provided"}

Create a detailed execution plan with the following structure:
1. Analyze what needs to be done
2. Break into logical, sequential steps
3. Identify dependencies between steps
4. Estimate token usage for each step

Respond with ONLY valid JSON in this exact format:
{{
  "title": "<concise plan title>",
  "description": "<brief overview of what will be accomplished>",
  "steps": [
    {{
      "id": 1,
      "title": "<step title>",
      "description": "<what this step does>",
      "estimated_tokens": <token estimate>,
      "dependencies": []
    }},
    {{
      "id": 2,
      "title": "<step title>",
      "description": "<what this step does>",
      "estimated_tokens": <token estimate>,
      "dependencies": [1]
    }}
  ]
}}

Guidelines:
- Steps should be specific and actionable
- Each step should have a clear outcome
- List step IDs that must complete before this step (dependencies)
- Estimate tokens conservatively (analysis: 2000, reading: 3000, editing: 4000)
- Maximum 10 steps for clarity
"""
        return prompt

    async def _get_plan_from_llm(self, prompt: str) -> str:
        """Get plan JSON from LLM.

        Args:
            prompt: Planning prompt

        Returns:
            JSON string from LLM
        """
        from .llm_client import ChatMessage

        messages = [ChatMessage(role="user", content=prompt)]

        # Use low temperature for consistent planning
        response = ""
        async for chunk in self.llm_client.stream_chat(
            messages, temperature=0.3, max_tokens=2000
        ):
            response += chunk

        return response

    def _parse_plan_response(self, response: str, user_query: str) -> TaskPlan:
        """Parse LLM response into TaskPlan.

        Args:
            response: JSON response from LLM
            user_query: Original user query

        Returns:
            Parsed TaskPlan
        """
        # Extract JSON from response (may have markdown code blocks)
        json_str = self._extract_json(response)

        try:
            data = json.loads(json_str)

            # Create PlanStep objects
            steps = []
            total_tokens = 0

            for step_data in data["steps"]:
                step = PlanStep(
                    id=step_data["id"],
                    title=step_data["title"],
                    description=step_data["description"],
                    estimated_tokens=step_data["estimated_tokens"],
                    dependencies=step_data.get("dependencies", []),
                )
                steps.append(step)
                total_tokens += step.estimated_tokens

            # Create TaskPlan
            plan = TaskPlan(
                title=data["title"],
                description=data["description"],
                steps=steps,
                total_estimated_tokens=total_tokens,
                created_at=datetime.now().isoformat(),
                user_query=user_query,
            )

            logger.info(f"Created plan with {len(steps)} steps, ~{total_tokens} tokens")
            return plan

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse plan JSON: {e}")
            # Create fallback plan
            return self._create_fallback_plan(user_query)

    def _extract_json(self, text: str) -> str:
        """Extract JSON from text (handles markdown code blocks).

        Args:
            text: Text potentially containing JSON

        Returns:
            Extracted JSON string
        """
        # Remove markdown code blocks if present
        if "```json" in text:
            start = text.find("```json") + 7
            end = text.find("```", start)
            return text[start:end].strip()
        elif "```" in text:
            start = text.find("```") + 3
            end = text.find("```", start)
            return text[start:end].strip()
        else:
            # Try to find JSON object
            start = text.find("{")
            end = text.rfind("}") + 1
            if start != -1 and end > start:
                return text[start:end]

        return text.strip()

    def _create_fallback_plan(self, user_query: str) -> TaskPlan:
        """Create a simple fallback plan if LLM fails.

        Args:
            user_query: User's query

        Returns:
            Simple TaskPlan
        """
        return TaskPlan(
            title="Execute Request",
            description=f"Execute: {user_query}",
            steps=[
                PlanStep(
                    id=1,
                    title="Analyze request",
                    description="Understand what needs to be done",
                    estimated_tokens=2000,
                ),
                PlanStep(
                    id=2,
                    title="Execute task",
                    description=user_query,
                    estimated_tokens=5000,
                    dependencies=[1],
                ),
            ],
            total_estimated_tokens=7000,
            created_at=datetime.now().isoformat(),
            user_query=user_query,
        )

    async def execute_plan(
        self,
        plan: TaskPlan,
        status_callback: Callable[[str], None] | None = None,
        confirm_callback: Callable[[str], bool] | None = None,
    ) -> bool:
        """Execute a plan step by step.

        Args:
            plan: TaskPlan to execute
            status_callback: Callback for status updates
            confirm_callback: Callback for step confirmation (returns True to continue)

        Returns:
            True if all steps completed successfully
        """
        self.current_plan = plan
        logger.info(f"Starting plan execution: {plan.title}")

        while True:
            # Get next step
            next_step = plan.get_next_step()

            if next_step is None:
                # No more steps available
                if plan.is_finished():
                    # All steps processed (completed, skipped, or failed)
                    logger.info("Plan execution finished")
                    return True
                else:
                    logger.warning("Plan blocked - no executable steps remaining")
                    return False

            # Confirm step if callback provided
            if confirm_callback:
                message = f"Execute step {next_step.id}: {next_step.title}?"
                if not confirm_callback(message):
                    logger.info(f"Step {next_step.id} skipped by user")
                    next_step.status = StepStatus.SKIPPED
                    continue

            # Update status
            if status_callback:
                status_callback("planning")

            plan.mark_step_in_progress(next_step.id)

            # Execute step
            try:
                if status_callback:
                    status_callback("processing")

                result = await self._execute_step(next_step, status_callback)
                plan.mark_step_complete(next_step.id, result)

            except Exception as e:
                logger.error(f"Step {next_step.id} failed: {e}")
                plan.mark_step_failed(next_step.id, str(e))

                # Ask if user wants to continue
                if confirm_callback:
                    if not confirm_callback(
                        "Step failed. Continue with remaining steps?"
                    ):
                        return False

        return plan.is_complete()

    async def _execute_step(
        self,
        step: PlanStep,
        status_callback: Callable[[str], None] | None = None,
    ) -> str:
        """Execute a single plan step.

        Args:
            step: Step to execute
            status_callback: Status update callback

        Returns:
            Result description
        """
        logger.info(f"Executing step {step.id}: {step.title}")

        # Update status to show what we're doing
        if status_callback:
            status_callback("analyzing")

        # Execute step directly via LLM (avoid recursion through process_user_input)
        try:
            from ..core.llm_client import ChatMessage

            messages = [
                ChatMessage(
                    role="system",
                    content="You are an AI coding assistant executing a planned step.",
                ),
                ChatMessage(
                    role="user",
                    content=f"Execute this task step:\n\n{step.description}\n\nProvide a clear response about what you did.",
                ),
            ]

            result = await self.llm_client.chat(messages=messages, temperature=0.7)

            if status_callback:
                status_callback("synthesizing")

            return result or "Step completed"

        except Exception as e:
            logger.error(f"Step execution failed: {e}")
            return f"Step failed: {str(e)}"

    def show_plan_preview(self, plan: TaskPlan) -> str:
        """Generate rich text preview of the plan.

        Args:
            plan: Plan to preview

        Returns:
            Formatted preview string
        """
        from io import StringIO

        from rich.console import Console
        from rich.table import Table

        # Create virtual console to capture output
        buffer = StringIO()
        console = Console(file=buffer, force_terminal=False, width=80)

        # Create table
        table = Table(title=f"Plan: {plan.title}", show_header=True)
        table.add_column("#", style="cyan", width=3)
        table.add_column("Step", style="white", width=40)
        table.add_column("Tokens", style="dim", width=8)
        table.add_column("Deps", style="yellow", width=8)

        for step in plan.steps:
            deps_str = (
                ",".join(str(d) for d in step.dependencies)
                if step.dependencies
                else "-"
            )
            table.add_row(
                str(step.id),
                step.title,
                f"~{step.estimated_tokens}",
                deps_str,
            )

        # Add summary row
        table.add_row(
            "",
            f"Total: {len(plan.steps)} steps",
            f"~{plan.total_estimated_tokens}",
            "",
            style="bold",
        )

        console.print(table)

        return buffer.getvalue()

    def get_plan_status(self) -> str:
        """Get current plan status summary.

        Returns:
            Status summary string
        """
        if not self.current_plan:
            return "No active plan"

        completed, total = self.current_plan.get_progress()
        percentage = self.current_plan.get_progress_percentage()

        status = f"Plan: {self.current_plan.title}\n"
        status += f"Progress: {completed}/{total} steps ({percentage:.1f}%)\n"

        if self.current_plan.is_complete():
            status += "Status: ✓ Complete"
        elif self.current_plan.has_failed_steps():
            status += "Status: ✗ Has failed steps"
        else:
            next_step = self.current_plan.get_next_step()
            if next_step:
                status += f"Next: Step {next_step.id} - {next_step.title}"
            else:
                status += "Status: Blocked (no executable steps)"

        return status
