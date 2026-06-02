"""PR 2b-1: model-compatibility parsing layer.

Covers the three tool-call dialects (server JSON / Hermes XML / shim JSON),
raw-text recovery when the server leaks <tool_call> tags, and <think> reasoning
handling — the things a daily-driver loop needs to not break on real models.
"""

from __future__ import annotations

from gerdsenai_cli.core.llm_client import ToolCall
from gerdsenai_cli.core.tool_parsing import (
    detect_tool_format,
    parse_model_output,
    strip_reasoning,
)

# --------------------------------------------------------------------------- #
# <think> reasoning handling
# --------------------------------------------------------------------------- #


def test_strip_reasoning_removes_think_block() -> None:
    clean, reasoning = strip_reasoning(
        "<think>Let me consider the options.</think>The answer is 42."
    )
    assert clean == "The answer is 42."
    assert "consider the options" in reasoning


def test_strip_reasoning_multiple_blocks() -> None:
    clean, reasoning = strip_reasoning("<think>a</think>X<think>b</think>Y")
    assert clean == "XY"
    assert "a" in reasoning and "b" in reasoning


def test_strip_reasoning_unclosed_think_is_dropped() -> None:
    """A truncated/cancelled stream may leave an unterminated <think>."""
    clean, reasoning = strip_reasoning("done<think>still thinking and cut off")
    assert clean == "done"
    assert "still thinking" in reasoning


def test_strip_reasoning_folds_in_server_reasoning_content() -> None:
    clean, reasoning = strip_reasoning("answer", reasoning_content="vLLM chain")
    assert clean == "answer"
    assert "vLLM chain" in reasoning


def test_strip_reasoning_no_think_is_noop() -> None:
    clean, reasoning = strip_reasoning("plain answer")
    assert clean == "plain answer"
    assert reasoning == ""


# --------------------------------------------------------------------------- #
# resolution order: server -> hermes -> shim -> prose
# --------------------------------------------------------------------------- #


def test_server_tool_calls_take_precedence() -> None:
    server = [ToolCall(id="s1", name="read_file", arguments={"path": "a.py"})]
    result = parse_model_output("some text", server_tool_calls=server)
    assert result.tool_calls == server


def test_hermes_xml_single_tool_call() -> None:
    text = '<tool_call>{"name": "read_file", "arguments": {"path": "a.py"}}</tool_call>'
    result = parse_model_output(text)
    assert result.has_tool_calls
    assert result.tool_calls[0].name == "read_file"
    assert result.tool_calls[0].arguments == {"path": "a.py"}


def test_hermes_xml_multiple_tool_calls() -> None:
    text = (
        '<tool_call>{"name": "read_file", "arguments": {"path": "a.py"}}</tool_call>\n'
        '<tool_call>{"name": "read_file", "arguments": {"path": "b.py"}}</tool_call>'
    )
    result = parse_model_output(text)
    assert len(result.tool_calls) == 2
    assert {c.arguments["path"] for c in result.tool_calls} == {"a.py", "b.py"}


def test_hermes_recovered_even_when_server_omits_tool_calls() -> None:
    """The vLLM streaming bug: tags leak as text with no structured tool_calls."""
    text = (
        "Sure, let me check.\n"
        '<tool_call>{"name": "search_files", "arguments": {"query": "auth"}}</tool_call>'
    )
    result = parse_model_output(text, server_tool_calls=None)
    assert result.tool_calls[0].name == "search_files"
    # The surrounding prose is kept but the tag is stripped from content.
    assert "<tool_call>" not in result.content
    assert "let me check" in result.content


def test_hermes_malformed_block_is_skipped() -> None:
    text = "<tool_call>{not valid json}</tool_call>"
    result = parse_model_output(text)
    assert not result.has_tool_calls
    # Degrades to a final answer rather than crashing.
    assert isinstance(result.content, str)


def test_think_then_hermes_tool_call() -> None:
    """A reasoning model thinks, then emits a Hermes tool call."""
    text = (
        "<think>The user wants file a.py. I'll read it.</think>\n"
        '<tool_call>{"name": "read_file", "arguments": {"path": "a.py"}}</tool_call>'
    )
    result = parse_model_output(text)
    assert result.tool_calls[0].name == "read_file"
    assert "wants file a.py" in result.reasoning
    # Reasoning never leaks into content or gets parsed as a call's text.
    assert "<think>" not in result.content


def test_shim_json_tool_call_still_works() -> None:
    result = parse_model_output('{"tool": "read_file", "arguments": {"path": "x"}}')
    assert result.tool_calls[0].name == "read_file"


def test_plain_prose_is_final_answer() -> None:
    result = parse_model_output("The bug is in main.py at line 42.")
    assert not result.has_tool_calls
    assert "main.py" in result.content


def test_server_tool_calls_with_reasoning() -> None:
    server = [ToolCall(id="s1", name="f", arguments={})]
    result = parse_model_output("<think>thinking</think>", server_tool_calls=server)
    assert result.tool_calls == server
    assert "thinking" in result.reasoning


# --------------------------------------------------------------------------- #
# format detection (advisory only)
# --------------------------------------------------------------------------- #


def test_detect_tool_format_hermes_models() -> None:
    assert detect_tool_format("qwen2.5-coder:7b") == "hermes"
    assert detect_tool_format("Hermes-4-70B") == "hermes"
    assert detect_tool_format("qwq-32b") == "hermes"


def test_detect_tool_format_default_openai() -> None:
    assert detect_tool_format("llama3.1:8b") == "openai"
    assert detect_tool_format("gpt-oss") == "openai"
    assert detect_tool_format(None) == "openai"
