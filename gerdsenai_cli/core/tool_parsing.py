"""Model-output compatibility layer for the agent loop.

Frontier local models don't agree on how to express a tool call:

- OpenAI-compatible servers (Ollama, vLLM, LM Studio) return structured
  ``tool_calls`` in the response JSON (handled by ``LLMClient._parse_tool_calls``).
- Qwen2.5 / Qwen3 and the Hermes 3/4 family emit **Hermes-style** XML in the
  text: ``<tool_call>{"name": ..., "arguments": {...}}</tool_call>`` (one or many).
  vLLM ships a server-side ``hermes`` parser for this, but it has known streaming
  bugs that leak the raw tags as text — so we parse the tags ourselves as a
  fallback even when talking to a "tool-aware" server.
- The prompt shim (for tool-less models) uses its own ``{"tool": ...}`` JSON.

On top of that, reasoning models (DeepSeek-R1, QwQ, Qwen3-thinking, DeepHermes)
wrap their chain-of-thought in ``<think>...</think>`` (or vLLM exposes it as a
separate ``reasoning_content`` field). If we tried to parse tool calls without
stripping that first, a think block would be mistaken for a final answer.

This module gives the loop one entry point, ``parse_model_output``, that copes
with all of the above and returns the same provider-agnostic ``ChatResult``.
"""

from __future__ import annotations

import json
import logging
import re

from .llm_client import ChatResult, ToolCall

logger = logging.getLogger(__name__)

_THINK_RE = re.compile(r"<think>(.*?)</think>", re.DOTALL | re.IGNORECASE)
_THINK_OPEN_UNCLOSED_RE = re.compile(r"<think>(.*)\Z", re.DOTALL | re.IGNORECASE)
_TOOL_CALL_RE = re.compile(r"<tool_call>\s*(.*?)\s*</tool_call>", re.DOTALL)


def strip_reasoning(text: str, reasoning_content: str | None = None) -> tuple[str, str]:
    """Split model text into (clean_text, reasoning).

    - Removes ``<think>...</think>`` blocks (any number) from ``text``.
    - Also tolerates an unterminated ``<think>`` (truncated stream) by dropping
      everything from the opening tag onward.
    - If the server already separated the chain-of-thought into
      ``reasoning_content`` (vLLM), that is folded into the returned reasoning.

    The returned ``clean_text`` is what tool-call parsing should run on; the
    ``reasoning`` is for the UI to surface dimly (never fed back to tool parsing).
    """
    reasonings: list[str] = []
    if reasoning_content:
        reasonings.append(reasoning_content.strip())

    def _collect(match: re.Match[str]) -> str:
        reasonings.append(match.group(1).strip())
        return ""

    clean = _THINK_RE.sub(_collect, text)
    # Drop a dangling, unclosed <think> (e.g. truncated/cancelled stream).
    unclosed = _THINK_OPEN_UNCLOSED_RE.search(clean)
    if unclosed:
        reasonings.append(unclosed.group(1).strip())
        clean = clean[: unclosed.start()]

    reasoning = "\n\n".join(r for r in reasonings if r)
    return clean.strip(), reasoning


def _parse_hermes_tool_calls(text: str) -> list[ToolCall]:
    """Extract Hermes ``<tool_call>{...}</tool_call>`` blocks from text.

    Returns one ToolCall per well-formed block; silently skips malformed JSON
    (a model that half-emits a tag shouldn't crash the turn).
    """
    calls: list[ToolCall] = []
    for raw in _TOOL_CALL_RE.findall(text):
        try:
            obj = json.loads(raw.strip())
        except json.JSONDecodeError:
            logger.debug(f"Skipping malformed Hermes tool_call block: {raw[:80]!r}")
            continue
        if not isinstance(obj, dict):
            continue
        name = obj.get("name") or obj.get("tool") or ""
        args = obj.get("arguments", obj.get("args", {}))
        if not name:
            continue
        calls.append(
            ToolCall(
                id=f"hermes_{len(calls)}",
                name=str(name),
                arguments=args if isinstance(args, dict) else {},
            )
        )
    return calls


def _strip_tool_call_tags(text: str) -> str:
    """Remove Hermes ``<tool_call>`` blocks, leaving any surrounding prose."""
    return _TOOL_CALL_RE.sub("", text).strip()


def parse_model_output(
    text: str,
    server_tool_calls: list[ToolCall] | None = None,
    reasoning_content: str | None = None,
) -> ChatResult:
    """Unified parse of one model turn into a ChatResult.

    Resolution order (most trustworthy first):
      1. ``server_tool_calls`` — already-structured calls from the server JSON.
      2. Hermes ``<tool_call>`` XML recovered from the raw text (covers servers
         whose own parser leaked the tags, and pure text endpoints).
      3. The shim's ``{"tool": ...}`` JSON object form.
      4. Otherwise: a final answer (the cleaned prose).

    ``<think>`` reasoning is stripped first and carried on the result so it can
    never be mistaken for a tool call or the final answer.
    """
    clean, reasoning = strip_reasoning(text or "", reasoning_content)

    # 1. Server already structured the calls.
    if server_tool_calls:
        return ChatResult(
            content=_strip_tool_call_tags(clean),
            tool_calls=list(server_tool_calls),
            reasoning=reasoning,
        )

    # 2. Hermes XML in the text (resilient to the vLLM streaming-parser bug).
    hermes = _parse_hermes_tool_calls(clean)
    if hermes:
        return ChatResult(
            content=_strip_tool_call_tags(clean),
            tool_calls=hermes,
            reasoning=reasoning,
        )

    # 3. Shim JSON object form ({"tool": ...} / {"final": ...}).
    from .tool_shim import parse_shim_response

    shim = parse_shim_response(clean)
    if shim.has_tool_calls:
        return ChatResult(
            content=shim.content, tool_calls=shim.tool_calls, reasoning=reasoning
        )

    # 4. Final answer.
    return ChatResult(content=shim.content or clean, reasoning=reasoning)


def detect_tool_format(model: str | None) -> str:
    """Heuristic tool dialect for a model name: 'hermes' | 'openai'.

    Qwen and Hermes families speak Hermes-style ``<tool_call>`` tags; everything
    else is assumed OpenAI-shape. Callers may override via a setting. This only
    decides which *prompt* hint / parse-preference to use — ``parse_model_output``
    always recovers tool calls regardless, so a wrong guess degrades, not breaks.
    """
    name = (model or "").lower()
    if any(tag in name for tag in ("qwen", "hermes", "qwq")):
        return "hermes"
    return "openai"
