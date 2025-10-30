# Phase 8d: Agent Intelligence Enhancement - Next Steps

## [COMPLETE] Phase 8d-1: Sophisticated Status Messages - COMPLETE

**Completed:** October 3, 2025  
**Branch:** `feature/agent-intelligence-enhancement`  
**Status:** Merged and tested 

### What Was Accomplished

1. **Status Message Module** (`gerdsenai_cli/utils/status_messages.py`)
   - 11 operation types with scholarly vocabulary
   - 100+ unique phrases with random selection
   - Context suffixes for 30% variation
   - Zero configuration needed

2. **Full Integration**
   - Console: `set_operation()` method
   - Agent: `status_callback` parameter
   - Main loop: Callback wiring
   - All 4 integration points verified 

3. **Documentation & Tests**
   - STATUS_MESSAGE_INTEGRATION.md (architecture guide)
   - test_status_demo.py (55 example messages)
   - test_status_integration_live.py (verification suite)
   - All tests passing 

### Example Output
```
Task: Cogitating possibilities via methodical inquiry...
Task: Deconstructing semantic topology exercising semantic judgment...
Task: Channeling cognitive flow...
```

---

## GOAL: Next Priority: Multi-Step Planning System

**Estimated Time:** 2-3 days  
**Complexity:** Medium-High  
**Value:** High (enables complex task automation)

### Overview

Implement an intelligent planning system that:
- Breaks complex requests into sequential steps
- Shows preview before execution
- Tracks progress through plan
- Allows user confirmation at each phase
- Integrates with status messages

### Architecture Design

```
User: "Refactor all commands to use dependency injection"
          ↓
    [Intent Detection] → High complexity task detected
          ↓
    [Task Planner] → Breaks into steps:
          ↓
    1. Analyze current command structure
    2. Identify common dependencies
    3. Design injection pattern
    4. Refactor base.py
    5. Update all command files
    6. Run tests
          ↓
    [Show Preview] → User reviews plan
          ↓
    [Confirm] → User approves
          ↓
    [Execute] → Step-by-step with status updates
          ↓
    [Track Progress] → 3/6 steps complete...
```

### Implementation Plan

#### Step 1: Create Core Planner Module (Day 1)

**File:** `gerdsenai_cli/core/planner.py`

```python
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional

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
    dependencies: List[int]  # Step IDs this depends on
    status: StepStatus = StepStatus.PENDING
    result: Optional[str] = None
    error: Optional[str] = None

@dataclass
class TaskPlan:
    """A complete multi-step plan."""
    title: str
    description: str
    steps: List[PlanStep]
    total_estimated_tokens: int
    created_at: str
    
    def get_next_step(self) -> Optional[PlanStep]:
        """Get the next pending step with satisfied dependencies."""
        # Implementation
        pass
    
    def mark_step_complete(self, step_id: int, result: str) -> None:
        """Mark a step as completed."""
        # Implementation
        pass
    
    def mark_step_failed(self, step_id: int, error: str) -> None:
        """Mark a step as failed."""
        # Implementation
        pass
    
    def get_progress(self) -> tuple[int, int]:
        """Get (completed, total) steps."""
        # Implementation
        pass

class TaskPlanner:
    """Plans and executes multi-step tasks."""
    
    def __init__(self, llm_client, agent):
        self.llm_client = llm_client
        self.agent = agent
        self.current_plan: Optional[TaskPlan] = None
    
    async def create_plan(self, user_request: str) -> TaskPlan:
        """Create a plan by asking LLM to break down the task."""
        # Prompt LLM to analyze task and create steps
        # Return TaskPlan object
        pass
    
    async def execute_plan(
        self, 
        plan: TaskPlan,
        status_callback=None,
        confirm_callback=None
    ) -> bool:
        """Execute a plan step by step."""
        # For each step:
        #   1. Check dependencies
        #   2. Call confirm_callback if needed
        #   3. Execute step
        #   4. Update status via status_callback
        #   5. Mark complete/failed
        pass
    
    def show_plan_preview(self, plan: TaskPlan) -> str:
        """Generate rich preview of the plan."""
        # Return formatted plan for display
        pass
```

#### Step 2: Add Planning Intent Detection (Day 1)

**File:** `gerdsenai_cli/commands/parser.py` (extend)

Add complexity detection:
```python
def detect_complexity(self, user_input: str) -> str:
    """Detect if query is simple/medium/complex.
    
    Returns:
        "simple", "medium", or "complex"
    """
    complex_keywords = [
        "refactor all", "update all", "add to all",
        "migrate", "convert all", "restructure",
        "implement feature", "add system", "create module"
    ]
    
    medium_keywords = [
        "refactor", "update multiple", "create several",
        "modify and test", "implement and test"
    ]
    
    # Check for indicators
    if any(kw in user_input.lower() for kw in complex_keywords):
        return "complex"
    elif any(kw in user_input.lower() for kw in medium_keywords):
        return "medium"
    else:
        return "simple"
```

#### Step 3: Add /plan Command (Day 1)

**File:** `gerdsenai_cli/commands/planning.py` (new)

```python
from .base import BaseCommand

class PlanCommand(BaseCommand):
    """Show current plan or create new plan."""
    
    name = "plan"
    description = "Create or show multi-step plan"
    usage = "/plan [show|create|continue|cancel]"
    
    async def execute(self, args: list[str]) -> str:
        if not args or args[0] == "show":
            return await self._show_current_plan()
        elif args[0] == "create":
            return await self._create_plan(" ".join(args[1:]))
        elif args[0] == "continue":
            return await self._continue_plan()
        elif args[0] == "cancel":
            return await self._cancel_plan()
        else:
            return self.usage
    
    async def _show_current_plan(self) -> str:
        """Show the current plan if any."""
        pass
    
    async def _create_plan(self, task: str) -> str:
        """Create a plan for the given task."""
        pass
    
    async def _continue_plan(self) -> str:
        """Continue executing current plan."""
        pass
    
    async def _cancel_plan(self) -> str:
        """Cancel current plan."""
        pass
```

#### Step 4: Integrate with Agent (Day 2)

**File:** `gerdsenai_cli/core/agent.py` (extend)

Add planning mode:
```python
class GerdsenAIAgent:
    def __init__(self, settings: Settings):
        # ... existing code ...
        self.planner = TaskPlanner(self.llm_client, self)
        self.planning_mode = False
    
    async def process_user_input_stream(
        self, 
        user_input: str,
        status_callback=None
    ):
        # Detect complexity
        complexity = self.intent_parser.detect_complexity(user_input)
        
        # If complex and not already in planning mode, suggest plan
        if complexity == "complex" and not self.planning_mode:
            # Ask user if they want to create a plan
            # If yes, create plan and enter planning mode
            pass
        
        # If in planning mode, execute next step
        if self.planning_mode and self.planner.current_plan:
            # Execute next step
            pass
        
        # Otherwise, normal processing
        # ... existing code ...
```

#### Step 5: Add UI Components (Day 2)

**File:** `gerdsenai_cli/ui/console.py` (extend)

Add plan display methods:
```python
class EnhancedConsole:
    def show_plan_preview(self, plan: TaskPlan) -> None:
        """Display plan preview with Rich formatting."""
        from rich.table import Table
        from rich.panel import Panel
        
        table = Table(title=f"Plan: {plan.title}")
        table.add_column("#", style="cyan")
        table.add_column("Step", style="white")
        table.add_column("Tokens", style="dim")
        
        for step in plan.steps:
            table.add_row(
                str(step.id),
                step.title,
                f"~{step.estimated_tokens}"
            )
        
        self.console.print(Panel(table))
    
    def show_plan_progress(self, plan: TaskPlan) -> None:
        """Show progress through plan."""
        completed, total = plan.get_progress()
        progress_bar = "" * completed + "" * (total - completed)
        
        self.console.print(
            f"Progress: [{completed}/{total}] {progress_bar}"
        )
```

#### Step 6: Testing (Day 3)

**File:** `tests/test_planner.py` (new)

```python
import pytest
from gerdsenai_cli.core.planner import TaskPlanner, TaskPlan, PlanStep

@pytest.mark.asyncio
async def test_create_simple_plan():
    """Test creating a simple plan."""
    # Test plan creation
    pass

@pytest.mark.asyncio
async def test_execute_plan_with_dependencies():
    """Test executing plan with step dependencies."""
    # Test dependency resolution
    pass

@pytest.mark.asyncio
async def test_plan_failure_handling():
    """Test handling step failures."""
    # Test error handling
    pass

@pytest.mark.asyncio
async def test_complexity_detection():
    """Test complexity detection."""
    queries = [
        ("what is this file", "simple"),
        ("refactor auth.py", "medium"),
        ("refactor all commands to use DI", "complex"),
    ]
    # Test detection accuracy
    pass
```

### Success Criteria

- [ ] User can request complex tasks
- [ ] System detects complexity and suggests planning
- [ ] Plan preview shows all steps with estimates
- [ ] User can approve/reject plan
- [ ] Execution proceeds step-by-step with status updates
- [ ] Progress displayed: "Step 3/6: Refactoring base.py..."
- [ ] Failed steps handled gracefully with option to retry
- [ ] /plan command shows current plan status
- [ ] Integration with status messages: "Planning execution sequence..."

### Example Usage

```
You: Refactor all commands to use dependency injection

GerdsenAI: This looks like a complex task. I can create a 
multi-step plan for you. Would you like to see the plan first? (y/n)

You: y

GerdsenAI: Here's the plan:

 Plan: Refactor Commands for Dependency Injection 
 #  Step                              Tokens             

 1  Analyze current command structure    ~2000          
 2  Identify common dependencies         ~1500          
 3  Design injection pattern             ~3000          
 4  Update base.py with new pattern      ~4000          
 5  Refactor agent.py command            ~3500          
 6  Refactor files.py command            ~3500          
 7  Refactor model.py command            ~3500          
 8  Run test suite                        ~1000          

 Total: 8 steps, ~22,000 tokens                         


Execute this plan? (y/n)

You: y

GerdsenAI: [Task: Planning execution sequence...]
Step 1/8: Analyzing current command structure...
[Task: Reading architectural patterns...]
...
```

### Integration with Status Messages

During plan execution, status messages will show:
- "Planning execution sequence..." (PLANNING)
- "Reading architectural patterns..." (READING)
- "Analyzing dependency structure..." (ANALYZING)
- "Synthesizing refactoring strategy..." (SYNTHESIZING)
- "Writing updated implementation..." (WRITING)

### Future Enhancements

- **Plan Templates**: Common patterns (e.g., "Add feature with tests")
- **Plan Persistence**: Save/load plans from disk
- **Parallel Steps**: Execute independent steps concurrently
- **Interactive Mode**: Ask questions during execution
- **Rollback**: Undo completed steps if later step fails

---

## [PLANNED] Remaining Phases Overview

### Phase 8d-3: Context Memory (Week 2)
- Track conversation history
- Remember discussed files
- Persist across sessions
- Auto-recall relevant context

### Phase 8d-4: Clarifying Questions (Week 2)
- Low confidence → ask user
- Suggest interpretations
- Learn from corrections
- Improve over time

### Phase 8d-5: Complexity Detection (Week 2)
- Auto-detect multi-step tasks
- Suggest planning mode
- Estimate effort
- Warn about impacts

### Phase 8d-6: Confirmation Dialogs (Week 3)
- Preview destructive operations
- Show diffs before changes
- Explicit user confirmation
- Undo capability

### Phase 8d-7: Proactive Suggestions (Week 3)
- Pattern-based recommendations
- Suggest tests/improvements
- Context-aware timing
- Non-intrusive presentation

---

## GOAL: Immediate Next Action

**Task:** Implement Multi-Step Planning System  
**Start:** Create `gerdsenai_cli/core/planner.py`  
**Goal:** Enable complex task automation with user approval

**Command to start:**
```bash
# Create new branch
git checkout -b feature/multi-step-planning

# Create planner module
touch gerdsenai_cli/core/planner.py

# Start implementing TaskPlanner class
```

---

## STATUS: Overall Progress

**Phase 8d: Agent Intelligence Enhancement**
- [COMPLETE] Status Messages (Complete)
- [IN PROGRESS] Multi-Step Planning (Next - 2-3 days)
- ⏳ Context Memory (Queued - 2 days)
- ⏳ Clarifying Questions (Queued - 2 days)
- ⏳ Complexity Detection (Queued - 1 day)
- ⏳ Confirmation Dialogs (Queued - 2 days)
- ⏳ Proactive Suggestions (Queued - 3 days)

**Estimated Total:** 14-16 days for complete Phase 8d

**Current Status:** 1/7 features complete (14%)
