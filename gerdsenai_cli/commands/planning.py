"""
Planning commands for multi-step task execution.
"""

from typing import Any

from .base import BaseCommand, CommandCategory


class PlanCommand(BaseCommand):
    """Create, show, and manage multi-step plans."""
    
    def __init__(self, agent: Any = None):
        """Initialize plan command.
        
        Args:
            agent: Agent instance (optional)
        """
        super().__init__()
        self.agent = agent
    
    @property
    def name(self) -> str:
        """Command name."""
        return "plan"
    
    @property
    def description(self) -> str:
        """Command description."""
        return "Create or manage multi-step execution plans"
    
    @property
    def category(self) -> CommandCategory:
        """Command category."""
        return CommandCategory.AGENT
    
    async def execute(self, args: list[str]) -> str:
        """Execute plan command.
        
        Args:
            args: Command arguments
            
        Returns:
            Command result message
        """
        if not args:
            return await self._show_current_plan()
        
        subcommand = args[0].lower()
        
        if subcommand == "show":
            return await self._show_current_plan()
        elif subcommand == "create":
            if len(args) < 2:
                return "Usage: /plan create <task description>"
            task = " ".join(args[1:])
            return await self._create_plan(task)
        elif subcommand == "continue":
            return await self._continue_plan()
        elif subcommand == "cancel":
            return await self._cancel_plan()
        elif subcommand == "status":
            return await self._show_status()
        else:
            return self.usage
    
    async def _show_current_plan(self) -> str:
        """Show the current plan if any.
        
        Returns:
            Plan preview or message
        """
        # Get planner from agent
        if not hasattr(self, 'agent') or not self.agent:
            return "Agent not available"
        
        if not hasattr(self.agent, 'planner') or not self.agent.planner:
            return "Planning system not initialized"
        
        planner = self.agent.planner
        
        if not planner.current_plan:
            return "No active plan. Use '/plan create <task>' to create one."
        
        # Show plan preview
        preview = planner.show_plan_preview(planner.current_plan)
        return preview
    
    async def _create_plan(self, task: str) -> str:
        """Create a plan for the given task.
        
        Args:
            task: Task description
            
        Returns:
            Plan creation result
        """
        # Get planner from agent
        if not hasattr(self, 'agent') or not self.agent:
            return "Agent not available"
        
        if not hasattr(self.agent, 'planner') or not self.agent.planner:
            return "Planning system not initialized"
        
        planner = self.agent.planner
        
        # Build context from project
        context = ""
        if hasattr(self.agent, 'context_manager'):
            # Get summary of project files
            files = self.agent.context_manager.get_tracked_files()
            if files:
                context = f"Project has {len(files)} tracked files"
        
        # Create plan
        plan = await planner.create_plan(task, context)
        planner.current_plan = plan
        
        # Show preview
        preview = planner.show_plan_preview(plan)
        
        result = f"Plan created: {plan.title}\n\n"
        result += preview
        result += "\n\nUse '/plan continue' to execute, or '/plan cancel' to discard."
        
        return result
    
    async def _continue_plan(self) -> str:
        """Continue executing current plan.
        
        Returns:
            Execution status
        """
        # Get planner from agent
        if not hasattr(self, 'agent') or not self.agent:
            return "Agent not available"
        
        if not hasattr(self.agent, 'planner') or not self.agent.planner:
            return "Planning system not initialized"
        
        planner = self.agent.planner
        
        if not planner.current_plan:
            return "No active plan. Use '/plan create <task>' to create one."
        
        plan = planner.current_plan
        
        if plan.is_complete():
            return "Plan is already complete!"
        
        # Execute plan (this will be called from agent with callbacks)
        return "Executing plan... (This feature requires agent integration)"
    
    async def _cancel_plan(self) -> str:
        """Cancel current plan.
        
        Returns:
            Cancellation message
        """
        # Get planner from agent
        if not hasattr(self, 'agent') or not self.agent:
            return "Agent not available"
        
        if not hasattr(self.agent, 'planner') or not self.agent.planner:
            return "Planning system not initialized"
        
        planner = self.agent.planner
        
        if not planner.current_plan:
            return "No active plan to cancel."
        
        plan_title = planner.current_plan.title
        planner.current_plan = None
        
        return f"Cancelled plan: {plan_title}"
    
    async def _show_status(self) -> str:
        """Show current plan status.
        
        Returns:
            Status summary
        """
        # Get planner from agent
        if not hasattr(self, 'agent') or not self.agent:
            return "Agent not available"
        
        if not hasattr(self.agent, 'planner') or not self.agent.planner:
            return "Planning system not initialized"
        
        planner = self.agent.planner
        
        return planner.get_plan_status()
