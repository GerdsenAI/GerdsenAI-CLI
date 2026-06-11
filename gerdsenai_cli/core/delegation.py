"""Sub-agent delegation: spawn a focused child tool-loop for a sub-task.

A turn (the model, via the ``delegate`` tool) or the user (via ``/delegate``) can
hand a self-contained sub-task to a fresh agent loop. The child runs the same
tools through the same ``confirm`` gate as the parent, so consent is preserved —
its edits and shell commands are individually gated exactly as the parent's are.

Recursion is bounded by ``delegation_max_depth``: at the cap, the child's registry
omits the ``delegate`` tool so a sub-agent cannot spawn another (belt-and-suspenders
on top of the explicit depth check here).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .agent import Agent

logger = logging.getLogger(__name__)


def delegation_enabled(agent: Agent) -> bool:
    """Whether sub-agent delegation is turned on (default True)."""
    return bool(agent.settings.get_preference("enable_delegation", True))


def delegation_max_depth(agent: Agent) -> int:
    """Maximum delegation nesting (default 1: the top agent may spawn one child)."""
    try:
        return max(0, int(agent.settings.get_preference("delegation_max_depth", 1)))
    except (TypeError, ValueError):
        return 1


async def run_delegation(agent: Agent, task: str, *, depth: int, max_depth: int) -> str:
    """Run a focused sub-agent loop for ``task`` and return its final answer.

    Args:
        agent: the live parent Agent (its client, settings, confirm gate, and
            context are reused — the child is not a separate process).
        task: the self-contained sub-task to hand off.
        depth: the child's depth (the parent is 0, so the first child is 1).
        max_depth: the configured cap; at/above it the child gets no delegate tool.

    Returns the sub-agent's final text, or a short message when the task is empty
    or the depth cap is exceeded.
    """
    from .agent_tools import build_default_registry
    from .tool_registry import run_agent_loop

    task = (task or "").strip()
    if not task:
        return "No task was provided to delegate."
    if depth > max_depth:
        return (
            f"Delegation depth limit ({max_depth}) reached; "
            "handle this sub-task directly instead of delegating further."
        )

    # The child registry includes the delegate tool only while still below the
    # cap, so a sub-agent at max depth cannot spawn another.
    child_registry = build_default_registry(agent, delegation_depth=depth)
    messages = agent._prepare_llm_messages(task)
    max_iter = int(agent.settings.get_preference("agent_loop_max_iterations", 10))

    logger.info("Delegating sub-task at depth %d: %s", depth, task[:80])
    result = await run_agent_loop(
        agent.llm_client,
        messages,
        child_registry,
        model=agent.settings.current_model or None,
        confirm=agent._tool_confirm,
        allow_tools=True,
        max_iterations=max_iter,
    )
    return result.content or "(the sub-agent finished without producing output)"
