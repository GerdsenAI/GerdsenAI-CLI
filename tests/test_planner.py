"""
Tests for multi-step task planning system.
"""

import json
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from gerdsenai_cli.core.planner import (
    StepStatus,
    PlanStep,
    TaskPlan,
    TaskPlanner,
)


class TestPlanStep:
    """Tests for PlanStep class."""

    def test_plan_step_creation(self):
        """Test creating a plan step."""
        step = PlanStep(
            id=1,
            title="Analyze code",
            description="Review the codebase structure",
            estimated_tokens=2000,
            dependencies=[],
        )

        assert step.id == 1
        assert step.title == "Analyze code"
        assert step.status == StepStatus.PENDING
        assert step.result is None
        assert step.error is None

    def test_plan_step_can_execute_no_dependencies(self):
        """Test step can execute when it has no dependencies."""
        step = PlanStep(
            id=1,
            title="Test",
            description="Test step",
            estimated_tokens=1000,
            dependencies=[],
        )

        assert step.can_execute(set())
        assert step.can_execute({2, 3})

    def test_plan_step_can_execute_with_dependencies(self):
        """Test step execution depends on completed steps."""
        step = PlanStep(
            id=3,
            title="Test",
            description="Test step",
            estimated_tokens=1000,
            dependencies=[1, 2],
        )

        assert not step.can_execute(set())
        assert not step.can_execute({1})
        assert not step.can_execute({2})
        assert step.can_execute({1, 2})
        assert step.can_execute({1, 2, 4})

    def test_plan_step_serialization(self):
        """Test step can be serialized and deserialized."""
        step = PlanStep(
            id=1,
            title="Analyze",
            description="Analyze code",
            estimated_tokens=2000,
            dependencies=[],
        )

        step_dict = step.to_dict()
        assert step_dict["id"] == 1
        assert step_dict["title"] == "Analyze"
        assert step_dict["status"] == "pending"

        restored = PlanStep.from_dict(step_dict)
        assert restored.id == step.id
        assert restored.title == step.title
        assert restored.status == step.status


class TestTaskPlan:
    """Tests for TaskPlan class."""

    def test_task_plan_creation(self):
        """Test creating a task plan."""
        steps = [
            PlanStep(1, "Step 1", "First step", 1000, []),
            PlanStep(2, "Step 2", "Second step", 2000, [1]),
            PlanStep(3, "Step 3", "Third step", 1500, [2]),
        ]

        plan = TaskPlan(
            title="Test Plan",
            description="A test plan",
            steps=steps,
            total_estimated_tokens=4500,
            created_at=datetime.now().isoformat(),
        )

        assert plan.title == "Test Plan"
        assert len(plan.steps) == 3
        assert plan.total_estimated_tokens == 4500

    def test_get_next_step_sequential(self):
        """Test getting next step in sequential plan."""
        steps = [
            PlanStep(1, "Step 1", "First", 1000, []),
            PlanStep(2, "Step 2", "Second", 1000, [1]),
            PlanStep(3, "Step 3", "Third", 1000, [2]),
        ]

        plan = TaskPlan(
            title="Test",
            description="Test",
            steps=steps,
            total_estimated_tokens=3000,
            created_at=datetime.now().isoformat(),
        )

        # First step should be available
        next_step = plan.get_next_step()
        assert next_step is not None
        assert next_step.id == 1

        # Mark first as complete
        plan.mark_step_complete(1, "Done")

        # Second step should be available
        next_step = plan.get_next_step()
        assert next_step is not None
        assert next_step.id == 2

        # Mark second as complete
        plan.mark_step_complete(2, "Done")

        # Third step should be available
        next_step = plan.get_next_step()
        assert next_step is not None
        assert next_step.id == 3

        # Mark third as complete
        plan.mark_step_complete(3, "Done")

        # No more steps
        next_step = plan.get_next_step()
        assert next_step is None

    def test_get_next_step_parallel(self):
        """Test getting next step with parallel execution."""
        steps = [
            PlanStep(1, "Step 1", "First", 1000, []),
            PlanStep(2, "Step 2", "Second", 1000, []),  # No dependency
            PlanStep(3, "Step 3", "Third", 1000, [1, 2]),
        ]

        plan = TaskPlan(
            title="Test",
            description="Test",
            steps=steps,
            total_estimated_tokens=3000,
            created_at=datetime.now().isoformat(),
        )

        # Step 1 should be available first
        next_step = plan.get_next_step()
        assert next_step.id == 1

        # Mark as in progress, step 2 should now be available
        plan.mark_step_in_progress(1)
        next_step = plan.get_next_step()
        assert next_step.id == 2

        # Complete both 1 and 2
        plan.mark_step_complete(1, "Done")
        plan.mark_step_complete(2, "Done")

        # Step 3 should be available
        next_step = plan.get_next_step()
        assert next_step.id == 3

    def test_mark_step_operations(self):
        """Test marking steps with different statuses."""
        steps = [
            PlanStep(1, "Step 1", "First", 1000, []),
        ]

        plan = TaskPlan(
            title="Test",
            description="Test",
            steps=steps,
            total_estimated_tokens=1000,
            created_at=datetime.now().isoformat(),
        )

        # Mark in progress
        plan.mark_step_in_progress(1)
        assert plan.steps[0].status == StepStatus.IN_PROGRESS

        # Mark complete
        plan.mark_step_complete(1, "Success")
        assert plan.steps[0].status == StepStatus.COMPLETED
        assert plan.steps[0].result == "Success"

    def test_mark_step_failed(self):
        """Test marking step as failed."""
        steps = [
            PlanStep(1, "Step 1", "First", 1000, []),
        ]

        plan = TaskPlan(
            title="Test",
            description="Test",
            steps=steps,
            total_estimated_tokens=1000,
            created_at=datetime.now().isoformat(),
        )

        plan.mark_step_failed(1, "Error occurred")
        assert plan.steps[0].status == StepStatus.FAILED
        assert plan.steps[0].error == "Error occurred"

    def test_get_progress(self):
        """Test getting plan progress."""
        steps = [
            PlanStep(1, "Step 1", "First", 1000, []),
            PlanStep(2, "Step 2", "Second", 1000, [1]),
            PlanStep(3, "Step 3", "Third", 1000, [2]),
        ]

        plan = TaskPlan(
            title="Test",
            description="Test",
            steps=steps,
            total_estimated_tokens=3000,
            created_at=datetime.now().isoformat(),
        )

        # Initial progress
        completed, total = plan.get_progress()
        assert completed == 0
        assert total == 3
        assert plan.get_progress_percentage() == 0.0

        # Complete first step
        plan.mark_step_complete(1, "Done")
        completed, total = plan.get_progress()
        assert completed == 1
        assert total == 3
        assert abs(plan.get_progress_percentage() - 33.33) < 0.1

        # Complete all steps
        plan.mark_step_complete(2, "Done")
        plan.mark_step_complete(3, "Done")
        completed, total = plan.get_progress()
        assert completed == 3
        assert total == 3
        assert plan.get_progress_percentage() == 100.0

    def test_is_complete(self):
        """Test checking if plan is complete."""
        steps = [
            PlanStep(1, "Step 1", "First", 1000, []),
            PlanStep(2, "Step 2", "Second", 1000, [1]),
        ]

        plan = TaskPlan(
            title="Test",
            description="Test",
            steps=steps,
            total_estimated_tokens=2000,
            created_at=datetime.now().isoformat(),
        )

        assert not plan.is_complete()

        plan.mark_step_complete(1, "Done")
        assert not plan.is_complete()

        plan.mark_step_complete(2, "Done")
        assert plan.is_complete()

    def test_has_failed_steps(self):
        """Test checking for failed steps."""
        steps = [
            PlanStep(1, "Step 1", "First", 1000, []),
            PlanStep(2, "Step 2", "Second", 1000, [1]),
        ]

        plan = TaskPlan(
            title="Test",
            description="Test",
            steps=steps,
            total_estimated_tokens=2000,
            created_at=datetime.now().isoformat(),
        )

        assert not plan.has_failed_steps()

        plan.mark_step_failed(1, "Error")
        assert plan.has_failed_steps()

    def test_plan_serialization(self):
        """Test plan serialization and deserialization."""
        steps = [
            PlanStep(1, "Step 1", "First", 1000, []),
            PlanStep(2, "Step 2", "Second", 1000, [1]),
        ]

        plan = TaskPlan(
            title="Test Plan",
            description="A test plan",
            steps=steps,
            total_estimated_tokens=2000,
            created_at=datetime.now().isoformat(),
            user_query="test query",
        )

        plan_dict = plan.to_dict()
        assert plan_dict["title"] == "Test Plan"
        assert len(plan_dict["steps"]) == 2

        restored = TaskPlan.from_dict(plan_dict)
        assert restored.title == plan.title
        assert len(restored.steps) == len(plan.steps)
        assert restored.user_query == plan.user_query


class TestTaskPlanner:
    """Tests for TaskPlanner class."""

    @pytest.fixture
    def mock_llm_client(self):
        """Create a mock LLM client."""
        client = AsyncMock()

        # Mock stream_chat to return a plan JSON
        async def mock_stream(messages, **kwargs):
            plan_json = {
                "title": "Refactor Code",
                "description": "Refactor all code files",
                "steps": [
                    {
                        "id": 1,
                        "title": "Analyze structure",
                        "description": "Analyze current code structure",
                        "estimated_tokens": 2000,
                        "dependencies": [],
                    },
                    {
                        "id": 2,
                        "title": "Create plan",
                        "description": "Create refactoring plan",
                        "estimated_tokens": 3000,
                        "dependencies": [1],
                    },
                ],
            }
            yield json.dumps(plan_json)

        client.stream_chat = mock_stream

        # Mock regular chat
        async def mock_chat(messages, **kwargs):
            return "Step executed successfully"

        client.chat = mock_chat

        return client

    @pytest.fixture
    def mock_agent(self):
        """Create a mock agent."""
        agent = MagicMock()
        return agent

    @pytest.fixture
    def planner(self, mock_llm_client, mock_agent):
        """Create a TaskPlanner instance."""
        return TaskPlanner(mock_llm_client, mock_agent)

    @pytest.mark.asyncio
    async def test_create_plan(self, planner):
        """Test creating a plan from user request."""
        plan = await planner.create_plan(
            user_request="Refactor all code files",
            context="Project has 10 Python files"
        )

        assert plan is not None
        assert plan.title == "Refactor Code"
        assert len(plan.steps) == 2
        assert plan.steps[0].id == 1
        assert plan.steps[1].dependencies == [1]
        assert plan.total_estimated_tokens == 5000

    @pytest.mark.asyncio
    async def test_create_plan_with_invalid_json(self, mock_llm_client, mock_agent):
        """Test creating plan when LLM returns invalid JSON."""
        # Override mock to return invalid JSON
        async def mock_stream_invalid(messages, **kwargs):
            yield "This is not valid JSON"

        mock_llm_client.stream_chat = mock_stream_invalid
        planner = TaskPlanner(mock_llm_client, mock_agent)

        plan = await planner.create_plan(
            user_request="Do something",
            context=""
        )

        # Should create fallback plan
        assert plan is not None
        assert plan.title == "Execute Request"
        assert len(plan.steps) >= 1

    @pytest.mark.asyncio
    async def test_execute_plan_success(self, planner):
        """Test executing a plan successfully."""
        steps = [
            PlanStep(1, "Step 1", "First", 1000, []),
            PlanStep(2, "Step 2", "Second", 1000, [1]),
        ]

        plan = TaskPlan(
            title="Test",
            description="Test",
            steps=steps,
            total_estimated_tokens=2000,
            created_at=datetime.now().isoformat(),
        )

        status_calls = []

        def status_callback(status):
            status_calls.append(status)

        result = await planner.execute_plan(
            plan,
            status_callback=status_callback,
        )

        assert result is True
        assert plan.is_complete()
        assert len(status_calls) > 0

    @pytest.mark.asyncio
    async def test_execute_plan_with_confirmation(self, planner):
        """Test executing plan with confirmation callback."""
        steps = [
            PlanStep(1, "Step 1", "First", 1000, []),
        ]

        plan = TaskPlan(
            title="Test",
            description="Test",
            steps=steps,
            total_estimated_tokens=1000,
            created_at=datetime.now().isoformat(),
        )

        confirm_calls = []

        def confirm_callback(message):
            confirm_calls.append(message)
            return True  # Always confirm

        result = await planner.execute_plan(
            plan,
            confirm_callback=confirm_callback,
        )

        assert result is True
        assert len(confirm_calls) > 0

    @pytest.mark.asyncio
    async def test_execute_plan_skip_step(self, planner):
        """Test skipping a step during execution."""
        steps = [
            PlanStep(1, "Step 1", "First", 1000, []),
            PlanStep(2, "Step 2", "Second", 1000, []),
        ]

        plan = TaskPlan(
            title="Test",
            description="Test",
            steps=steps,
            total_estimated_tokens=2000,
            created_at=datetime.now().isoformat(),
        )

        confirm_count = [0]

        def confirm_callback(message):
            confirm_count[0] += 1
            # Skip first step, execute second
            if confirm_count[0] == 1:
                return False  # Skip first
            return True  # Execute others

        result = await planner.execute_plan(
            plan,
            confirm_callback=confirm_callback,
        )

        # Should complete since step 2 has no dependencies
        assert result is True
        assert plan.steps[0].status == StepStatus.SKIPPED
        assert plan.steps[1].status == StepStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_execute_plan_with_failure(self, planner, mock_llm_client):
        """Test plan execution with step failure.

        Note: _execute_step catches exceptions internally and returns an error message,
        so the step is marked as COMPLETED (not FAILED) with an error result.
        """
        # Make chat fail
        async def mock_chat_fail(messages, **kwargs):
            raise Exception("LLM error")

        mock_llm_client.chat = mock_chat_fail

        steps = [
            PlanStep(1, "Step 1", "First", 1000, []),
        ]

        plan = TaskPlan(
            title="Test",
            description="Test",
            steps=steps,
            total_estimated_tokens=1000,
            created_at=datetime.now().isoformat(),
        )

        result = await planner.execute_plan(plan)

        # Plan should complete even though step failed (error is caught internally)
        assert result is True
        # Step is marked as COMPLETED (with error message in result)
        assert plan.steps[0].status == StepStatus.COMPLETED
        # Result should contain error message
        assert "failed" in plan.steps[0].result.lower() or "error" in plan.steps[0].result.lower()

    def test_show_plan_preview(self, planner):
        """Test generating plan preview."""
        steps = [
            PlanStep(1, "Step 1", "First", 1000, []),
            PlanStep(2, "Step 2", "Second", 2000, [1]),
        ]

        plan = TaskPlan(
            title="Test Plan",
            description="A test plan",
            steps=steps,
            total_estimated_tokens=3000,
            created_at=datetime.now().isoformat(),
        )

        preview = planner.show_plan_preview(plan)

        assert "Test Plan" in preview
        assert "Step 1" in preview
        assert "Step 2" in preview
        assert "~1000" in preview or "1000" in preview
        assert "~2000" in preview or "2000" in preview

    def test_get_plan_status_no_plan(self, planner):
        """Test getting status with no active plan."""
        status = planner.get_plan_status()
        assert "No active plan" in status

    def test_get_plan_status_with_plan(self, planner):
        """Test getting status with active plan."""
        steps = [
            PlanStep(1, "Step 1", "First", 1000, []),
            PlanStep(2, "Step 2", "Second", 1000, [1]),
        ]

        plan = TaskPlan(
            title="Test Plan",
            description="Test",
            steps=steps,
            total_estimated_tokens=2000,
            created_at=datetime.now().isoformat(),
        )

        planner.current_plan = plan

        status = planner.get_plan_status()
        assert "Test Plan" in status
        assert "0/2" in status or "Progress" in status

    def test_extract_json_with_markdown(self, planner):
        """Test extracting JSON from markdown code blocks."""
        text = """
Here is the plan:

```json
{
  "title": "Test",
  "steps": []
}
```

That's the plan!
"""

        extracted = planner._extract_json(text)
        parsed = json.loads(extracted)
        assert parsed["title"] == "Test"

    def test_extract_json_plain(self, planner):
        """Test extracting plain JSON."""
        text = '{"title": "Test", "steps": []}'

        extracted = planner._extract_json(text)
        parsed = json.loads(extracted)
        assert parsed["title"] == "Test"

    def test_create_fallback_plan(self, planner):
        """Test creating fallback plan."""
        plan = planner._create_fallback_plan("Do something")

        assert plan is not None
        assert "Execute Request" in plan.title
        assert len(plan.steps) >= 1
        assert plan.total_estimated_tokens > 0


class TestComplexityDetection:
    """Tests for complexity detection (in IntentParser)."""

    @pytest.fixture
    def intent_parser(self):
        """Create IntentParser instance."""
        from gerdsenai_cli.core.agent import IntentParser
        return IntentParser()

    def test_detect_simple_complexity(self, intent_parser):
        """Test detecting simple queries."""
        simple_queries = [
            "what is this file",
            "show me main.py",
            "explain this function",
            "read agent.py",
        ]

        for query in simple_queries:
            complexity = intent_parser.detect_complexity(query)
            assert complexity == "simple", f"Failed for: {query}"

    def test_detect_medium_complexity(self, intent_parser):
        """Test detecting medium complexity queries."""
        medium_queries = [
            "refactor the auth module",
            "update multiple config files",
            "create several test files",
            "modify and test the feature",
        ]

        for query in medium_queries:
            complexity = intent_parser.detect_complexity(query)
            assert complexity == "medium", f"Failed for: {query}"

    def test_detect_complex_complexity(self, intent_parser):
        """Test detecting complex queries."""
        complex_queries = [
            "refactor all command files to use dependency injection",
            "migrate the entire project to use async",
            "restructure all modules",
            "implement feature with full test coverage",
            "integrate authentication system across all endpoints",
        ]

        for query in complex_queries:
            complexity = intent_parser.detect_complexity(query)
            assert complexity == "complex", f"Failed for: {query}"
