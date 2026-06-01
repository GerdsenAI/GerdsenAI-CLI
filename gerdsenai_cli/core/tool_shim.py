"""Prompt-based tool-calling shim for models without native function-calling.

Local endpoints vary: some models speak the OpenAI ``tools`` schema, many don't.
This shim lets the agent loop work everywhere by *prompting* a tool-less model to
emit a small JSON object describing which tool to call (or that it's done), then
parsing that back into the same :class:`ChatResult` the native path returns.

It is deliberately forgiving: a model that just answers in prose yields a
``ChatResult`` with that prose and no tool calls (i.e. "final answer"), so a turn
never hard-fails just because the model ignored the protocol.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from .llm_client import ChatMessage, ChatResult, LLMClient, ToolCall

logger = logging.getLogger(__name__)

_SHIM_SYSTEM_TEMPLATE = """You can use tools to help answer the user. The available tools are:

{tool_descriptions}

To call a tool, respond with ONLY a JSON object (no prose, no markdown fences):
{{"tool": "<tool_name>", "arguments": {{<args>}}}}

To give your final answer to the user instead of calling a tool, respond with:
{{"final": "<your answer text>"}}

Rules:
- Respond with exactly one JSON object and nothing else.
- Only call a tool from the list above, with the arguments it expects.
- When you have enough information, use the "final" form to answer."""


def _describe_tools(tools: list[dict[str, Any]]) -> str:
    """Render OpenAI-shape tool schemas into a compact text description."""
    lines: list[str] = []
    for tool in tools:
        fn = tool.get("function", tool)
        name = fn.get("name", "?")
        desc = fn.get("description", "")
        params = fn.get("parameters", {}).get("properties", {})
        arg_names = ", ".join(params.keys()) if params else "none"
        lines.append(f"- {name}: {desc} (arguments: {arg_names})")
    return "\n".join(lines)


def build_shim_messages(
    messages: list[ChatMessage], tools: list[dict[str, Any]]
) -> list[ChatMessage]:
    """Prepend the tool-protocol instruction to a copy of the message list.

    Merges into an existing leading system message when present, so we don't
    stack two system turns (some local servers only honor the first).
    """
    instruction = _SHIM_SYSTEM_TEMPLATE.format(tool_descriptions=_describe_tools(tools))
    out = list(messages)
    if out and out[0].role == "system":
        out[0] = ChatMessage(
            role="system", content=f"{out[0].content}\n\n{instruction}"
        )
    else:
        out.insert(0, ChatMessage(role="system", content=instruction))
    return out


def _extract_json_object(text: str) -> dict[str, Any] | None:
    """Best-effort extraction of a single JSON object from model text.

    Handles bare objects and ```json / ``` fenced blocks (reusing the same
    tolerant approach as the existing intent parser).
    """
    candidates = [
        r"```json\s*\n?(.*?)\n?```",
        r"```\s*\n?(.*?)\n?```",
        r"(\{.*\})",
    ]
    for pattern in candidates:
        match = re.search(pattern, text, re.DOTALL)
        if not match:
            continue
        try:
            parsed = json.loads(match.group(1).strip())
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            continue
    return None


def parse_shim_response(text: str) -> ChatResult:
    """Parse a shimmed model reply into a ChatResult.

    - ``{"tool": ..., "arguments": ...}`` -> a single ToolCall.
    - ``{"final": "..."}`` -> content only (final answer).
    - anything else (prose, unparseable) -> treated as a final answer with the
      raw text, so the loop terminates gracefully instead of erroring.
    """
    obj = _extract_json_object(text)
    if obj is None:
        return ChatResult(content=text.strip())

    if "tool" in obj and obj.get("tool"):
        args = obj.get("arguments", {})
        return ChatResult(
            content="",
            tool_calls=[
                ToolCall(
                    id="shim_call",
                    name=str(obj["tool"]),
                    arguments=args if isinstance(args, dict) else {},
                )
            ],
        )
    if "final" in obj:
        return ChatResult(content=str(obj["final"]))

    # Valid JSON but not our protocol — surface it as the answer.
    return ChatResult(content=text.strip())


async def chat_with_tools_shim(
    client: LLMClient,
    messages: list[ChatMessage],
    tools: list[dict[str, Any]],
    model: str | None = None,
    temperature: float = 0.7,
    max_tokens: int | None = None,
) -> ChatResult:
    """Run one tool-aware turn against a tool-less model via prompting.

    Uses the plain :meth:`LLMClient.chat` under the hood, so it works on any
    endpoint. Returns the same ChatResult shape as the native path.
    """
    shimmed = build_shim_messages(messages, tools)
    text = await client.chat(
        shimmed, model=model, temperature=temperature, max_tokens=max_tokens
    )
    if not text:
        return ChatResult()
    return parse_shim_response(text)
