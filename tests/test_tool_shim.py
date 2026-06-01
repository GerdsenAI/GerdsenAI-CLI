"""Phase 1b: the prompt-based tool shim (works on tool-less models).

Verifies the shim turns a tool request into a JSON-protocol prompt, and parses
the model's reply (tool call / final / prose / fenced JSON) back into the same
ChatResult the native path returns.
"""

from __future__ import annotations

from typing import Any

import pytest

from gerdsenai_cli.core.llm_client import ChatMessage, ChatResult
from gerdsenai_cli.core.tool_shim import (
    build_shim_messages,
    chat_with_tools_shim,
    parse_shim_response,
)

_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a file",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
            },
        },
    }
]


# --------------------------------------------------------------------------- #
# prompt construction
# --------------------------------------------------------------------------- #


def test_build_shim_messages_inserts_system_when_absent() -> None:
    msgs = [ChatMessage(role="user", content="read a.py")]
    out = build_shim_messages(msgs, _TOOLS)
    assert out[0].role == "system"
    assert "read_file" in out[0].content
    assert "path" in out[0].content  # argument names rendered
    # original user message preserved after the injected system turn
    assert out[1].content == "read a.py"


def test_build_shim_messages_merges_into_existing_system() -> None:
    msgs = [
        ChatMessage(role="system", content="You are helpful."),
        ChatMessage(role="user", content="hi"),
    ]
    out = build_shim_messages(msgs, _TOOLS)
    # Still exactly one system message (merged, not stacked).
    assert sum(1 for m in out if m.role == "system") == 1
    assert "You are helpful." in out[0].content
    assert "read_file" in out[0].content


# --------------------------------------------------------------------------- #
# response parsing
# --------------------------------------------------------------------------- #


def test_parse_tool_call_object() -> None:
    result = parse_shim_response('{"tool": "read_file", "arguments": {"path": "a.py"}}')
    assert result.has_tool_calls
    assert result.tool_calls[0].name == "read_file"
    assert result.tool_calls[0].arguments == {"path": "a.py"}


def test_parse_final_answer() -> None:
    result = parse_shim_response('{"final": "the answer is 42"}')
    assert not result.has_tool_calls
    assert result.content == "the answer is 42"


def test_parse_fenced_json_tool_call() -> None:
    text = '```json\n{"tool": "read_file", "arguments": {"path": "x"}}\n```'
    result = parse_shim_response(text)
    assert result.tool_calls[0].name == "read_file"


def test_parse_plain_prose_becomes_final_answer() -> None:
    """A model that ignores the protocol and answers in prose still terminates."""
    result = parse_shim_response("I think the bug is in main.py.")
    assert not result.has_tool_calls
    assert "bug is in main.py" in result.content


def test_parse_tool_call_with_non_dict_arguments_is_empty() -> None:
    result = parse_shim_response('{"tool": "read_file", "arguments": "oops"}')
    assert result.tool_calls[0].arguments == {}


# --------------------------------------------------------------------------- #
# end-to-end against a fake client
# --------------------------------------------------------------------------- #


class _FakeClient:
    def __init__(self, reply: str) -> None:
        self.reply = reply
        self.seen_messages: list[ChatMessage] | None = None

    async def chat(self, messages: list[ChatMessage], **kwargs: Any) -> str:
        self.seen_messages = messages
        return self.reply


@pytest.mark.asyncio
async def test_chat_with_tools_shim_tool_call() -> None:
    client = _FakeClient('{"tool": "read_file", "arguments": {"path": "a.py"}}')
    result = await chat_with_tools_shim(
        client,  # type: ignore[arg-type]
        [ChatMessage(role="user", content="read a.py")],
        _TOOLS,
        model="some-local-model",
    )
    assert isinstance(result, ChatResult)
    assert result.tool_calls[0].name == "read_file"
    # The protocol instruction was actually prepended.
    assert client.seen_messages is not None
    assert client.seen_messages[0].role == "system"
    assert "read_file" in client.seen_messages[0].content


@pytest.mark.asyncio
async def test_chat_with_tools_shim_empty_reply_returns_empty() -> None:
    client = _FakeClient("")
    result = await chat_with_tools_shim(
        client,  # type: ignore[arg-type]
        [ChatMessage(role="user", content="hi")],
        _TOOLS,
    )
    assert isinstance(result, ChatResult)
    assert not result.has_tool_calls
    assert result.content == ""


# --------------------------------------------------------------------------- #
# Anthropic tool-schema conversion (pure; no SDK)
# --------------------------------------------------------------------------- #


def test_to_anthropic_tool_converts_openai_shape() -> None:
    from gerdsenai_cli.core.providers.anthropic import _to_anthropic_tool

    converted = _to_anthropic_tool(_TOOLS[0])
    assert converted["name"] == "read_file"
    assert converted["description"] == "Read a file"
    # OpenAI 'parameters' becomes Anthropic 'input_schema'.
    assert converted["input_schema"]["properties"] == {"path": {"type": "string"}}
    assert "function" not in converted


def test_to_anthropic_tool_passes_through_native_shape() -> None:
    from gerdsenai_cli.core.providers.anthropic import _to_anthropic_tool

    native = {"name": "f", "description": "d", "input_schema": {"type": "object"}}
    assert _to_anthropic_tool(native) == native
