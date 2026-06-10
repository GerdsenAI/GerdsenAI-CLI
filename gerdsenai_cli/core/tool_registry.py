"""Tool registry and the agentic tool-use loop.

This is the heart of the agent: instead of classifying a single intent and
running one hardcoded handler, the model is given a set of *tools* and driven in
a bounded loop — call a tool, observe its result, call another, until it produces
a final answer.

Design notes:
- Tools are provider-agnostic. Schemas are emitted in OpenAI ``function`` shape
  (the app's internal lingua franca); native providers and the prompt shim both
  consume that shape (see ``core.tool_shim`` and ``LLMClient.chat_with_tools``).
- The loop never assumes native tool support: it uses ``chat_with_tools`` when
  the model supports it and falls back to the prompt shim otherwise, so it is
  safe to run on any local endpoint.
- Autonomy is gated by a ``confirm`` callback, not baked in: read-only tools run
  freely; mutating tools (edit/create/run_command) are routed through ``confirm``
  so ExecutionMode / the existing ConfirmationEngine stays the guardrail.
"""

from __future__ import annotations

import inspect
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from .llm_client import ChatMessage, ChatResult, LLMClient
from .tool_shim import chat_with_tools_shim

logger = logging.getLogger(__name__)

# A tool implementation: takes parsed arguments, returns a result string.
ToolFunc = Callable[..., Awaitable[str]]
# Confirm gate for mutating tools: (tool_name, args) -> allowed?
ConfirmFunc = Callable[[str, dict[str, Any]], Awaitable[bool]]


@dataclass
class Tool:
    """A single callable tool exposed to the model."""

    name: str
    description: str
    parameters: dict[str, Any]  # JSON-schema for the arguments object
    func: ToolFunc
    mutating: bool = False  # if True, routed through the confirm gate

    def to_schema(self) -> dict[str, Any]:
        """Render as an OpenAI-shape function tool schema."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }

    async def run(self, arguments: dict[str, Any]) -> str:
        """Invoke the tool. Implementations are async (return Awaitable[str])."""
        return await self.func(**arguments)


@dataclass
class ToolRegistry:
    """A named collection of tools."""

    tools: dict[str, Tool] = field(default_factory=dict)

    def register(self, tool: Tool) -> None:
        self.tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        return self.tools.get(name)

    def schemas(self) -> list[dict[str, Any]]:
        return [t.to_schema() for t in self.tools.values()]

    def __len__(self) -> int:
        return len(self.tools)


@dataclass
class LoopResult:
    """Outcome of an agent-loop run."""

    content: str
    iterations: int
    tool_calls_made: int
    stopped_reason: str  # "final" | "max_iterations" | "error" | "empty"
    reasoning: str = ""  # chain-of-thought from the final model turn (display-only)


async def _supports_native_tools(client: LLMClient) -> bool:
    """Best-effort: does the active model advertise native tool support?

    Defaults to False (use the shim) when unknown — the shim works everywhere,
    so this only ever opts *into* the native path when we're confident.
    """
    caps = getattr(client, "get_capabilities", None)
    if caps is None:
        return False
    try:
        result = caps()
        if inspect.isawaitable(result):
            result = await result
        return bool(getattr(result, "supports_tools", False))
    except Exception:
        return False


async def run_agent_loop(
    client: LLMClient,
    messages: list[ChatMessage],
    registry: ToolRegistry,
    *,
    model: str | None = None,
    confirm: ConfirmFunc | None = None,
    allow_tools: bool = True,
    max_iterations: int = 10,
    use_native_tools: bool | None = None,
    on_event: Callable[[str, dict[str, Any]], None] | None = None,
) -> LoopResult:
    """Drive the model in a bounded tool-use loop.

    Args:
        client: LLM client (must expose ``chat`` and ``chat_with_tools``).
        messages: Conversation so far (system + history + new user turn).
        registry: Tools the model may call.
        model: Model id override.
        confirm: Async gate for *mutating* tools; if it returns False the tool is
            skipped and the model is told it was denied. Read-only tools bypass it.
            When None, mutating tools are allowed (caller opted out of gating).
        allow_tools: If False (e.g. CHAT mode), run a single plain completion with
            no tools — pure conversation.
        max_iterations: Safety cap on tool round-trips.
        use_native_tools: Force native (True) / shim (False); auto-detect if None.
        on_event: Optional observer for ("tool_call"|"tool_result"|"final", data).

    Returns:
        LoopResult with the final assistant text and loop telemetry.
    """
    convo = list(messages)

    # CHAT mode / no tools: a single plain completion, no loop.
    if not allow_tools or len(registry) == 0:
        text = await client.chat(convo, model=model) or ""
        return LoopResult(
            content=text,
            iterations=0,
            tool_calls_made=0,
            stopped_reason="final" if text else "empty",
        )

    native = (
        use_native_tools
        if use_native_tools is not None
        else await _supports_native_tools(client)
    )
    schemas = registry.schemas()
    tool_calls_made = 0

    for iteration in range(1, max_iterations + 1):
        if native:
            result: ChatResult = await client.chat_with_tools(
                convo, tools=schemas, model=model
            )
        else:
            result = await chat_with_tools_shim(client, convo, schemas, model=model)

        if not result.has_tool_calls:
            # The model gave a final answer (or nothing).
            if on_event and result.content:
                on_event("final", {"content": result.content})
            return LoopResult(
                content=result.content,
                iterations=iteration,
                tool_calls_made=tool_calls_made,
                stopped_reason="final" if result.content else "empty",
                reasoning=result.reasoning,
            )

        # Record the assistant's tool-call turn so the model sees its own calls.
        convo.append(
            ChatMessage(
                role="assistant",
                content=result.content,
                tool_calls=[
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {"name": tc.name, "arguments": tc.arguments},
                    }
                    for tc in result.tool_calls
                ],
            )
        )

        for call in result.tool_calls:
            tool_calls_made += 1
            tool = registry.get(call.name)
            if tool is None:
                observation = f"Error: unknown tool '{call.name}'."
            elif (
                tool.mutating
                and confirm is not None
                and not await confirm(call.name, call.arguments)
            ):
                observation = (
                    f"The user declined to run '{call.name}'. "
                    "Do not retry it; consider an alternative or ask the user."
                )
            else:
                if on_event:
                    on_event("tool_call", {"name": call.name, "args": call.arguments})
                try:
                    observation = await tool.run(call.arguments)
                except Exception as e:  # a tool failing must not kill the loop
                    logger.warning(f"Tool '{call.name}' raised: {e}")
                    observation = f"Error running '{call.name}': {e}"
                if on_event:
                    on_event("tool_result", {"name": call.name, "result": observation})

            convo.append(
                ChatMessage(role="tool", content=observation, tool_call_id=call.id)
            )

    # Hit the iteration cap without a final answer.
    logger.info(f"Agent loop hit max_iterations={max_iterations}")
    return LoopResult(
        content="(Stopped: reached the maximum number of tool steps for this turn.)",
        iterations=max_iterations,
        tool_calls_made=tool_calls_made,
        stopped_reason="max_iterations",
    )
