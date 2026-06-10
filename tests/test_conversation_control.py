"""Tests for ConversationControl rendering and streaming-segment styling.

ConversationControl instantiates headless (no running Application), so its
message bookkeeping and FormattedText output are pure-function testable. These
tests pin the styled-segment rendering added with the streamed agent loop
(reasoning dim, tool status, answer text), the emoji-strip rule, finalize
edge cases, and the ``system_info`` rendering (previously set-but-never-shown).
"""

from __future__ import annotations

import pytest

from gerdsenai_cli.ui.prompt_toolkit_tui import ConversationControl, PromptToolkitTUI


@pytest.fixture
def conv() -> ConversationControl:
    return ConversationControl()


@pytest.fixture
def tui() -> PromptToolkitTUI:
    return PromptToolkitTUI()


def _styles_for(formatted, needle: str) -> list[str]:
    """Return the style strings of every fragment whose text contains needle."""
    return [style for style, text in formatted if needle in text]


# --------------------------------------------------------------------------- #
# streaming-segment styling by kind
# --------------------------------------------------------------------------- #


def test_text_segment_feeds_streaming_message(conv: ConversationControl) -> None:
    conv.start_streaming("assistant")
    conv.append_streaming("the answer", "text")
    assert conv.streaming_message == "the answer"
    assert conv.streaming_segments == [("text", "the answer")]


def test_reasoning_and_tool_segments_do_not_feed_streaming_message(
    conv: ConversationControl,
) -> None:
    """Only 'text' accumulates into streaming_message; the rest are display-only."""
    conv.start_streaming("assistant")
    conv.append_streaming("answer ", "text")
    conv.append_streaming("internal thought", "reasoning")
    conv.append_streaming("calling read_file", "tool")
    # The answer-only contract: reasoning/tool never land in streaming_message.
    assert conv.streaming_message == "answer "
    # But all three are recorded as segments, in order.
    assert conv.streaming_segments == [
        ("text", "answer "),
        ("reasoning", "internal thought"),
        ("tool", "calling read_file"),
    ]


def test_segments_render_with_distinct_styles(conv: ConversationControl) -> None:
    conv.start_streaming("assistant")
    conv.append_streaming("ANSWERTEXT", "text")
    conv.append_streaming("REASONTEXT", "reasoning")
    conv.append_streaming("TOOLTEXT", "tool")

    formatted = conv.get_formatted_text()
    assert "class:ai-text" in _styles_for(formatted, "ANSWERTEXT")
    assert "class:dim" in _styles_for(formatted, "REASONTEXT")
    assert "class:tool-status" in _styles_for(formatted, "TOOLTEXT")


def test_render_falls_back_to_plain_text_without_segments(
    conv: ConversationControl,
) -> None:
    """A legacy stream that never recorded segments still renders its text."""
    conv.start_streaming("assistant")
    # Simulate the legacy path: streaming_message set without segment recording.
    conv.streaming_message = "LEGACYSTREAM"
    conv.streaming_segments = []
    formatted = conv.get_formatted_text()
    assert "class:ai-text" in _styles_for(formatted, "LEGACYSTREAM")


# --------------------------------------------------------------------------- #
# thinking toggle (TUI level: reasoning chunks are dropped when disabled)
# --------------------------------------------------------------------------- #


def test_thinking_disabled_drops_reasoning_chunks(tui: PromptToolkitTUI) -> None:
    tui.thinking_enabled = False
    tui.conversation.start_streaming("assistant")
    tui.append_streaming_chunk("visible answer", "text")
    tui.append_streaming_chunk("hidden reasoning", "reasoning")
    kinds = [k for k, _t in tui.conversation.streaming_segments]
    assert "reasoning" not in kinds
    assert tui.conversation.streaming_message == "visible answer"


def test_thinking_enabled_keeps_reasoning_chunks(tui: PromptToolkitTUI) -> None:
    tui.thinking_enabled = True
    tui.conversation.start_streaming("assistant")
    tui.append_streaming_chunk("answer", "text")
    tui.append_streaming_chunk("reasoning shown", "reasoning")
    segments = tui.conversation.streaming_segments
    assert ("reasoning", "reasoning shown") in segments


# --------------------------------------------------------------------------- #
# emoji strip
# --------------------------------------------------------------------------- #


def test_emoji_stripped_from_streamed_assistant_text(conv: ConversationControl) -> None:
    conv.start_streaming("assistant")
    conv.append_streaming("done \U0001f600 here", "text")
    assert "\U0001f600" not in conv.streaming_message
    assert "done" in conv.streaming_message and "here" in conv.streaming_message


def test_emoji_stripped_from_completed_assistant_message(
    conv: ConversationControl,
) -> None:
    conv.add_message("assistant", "ship it \U0001f680")
    content = conv.messages[-1][1]
    assert "\U0001f680" not in content
    assert "ship it" in content


# --------------------------------------------------------------------------- #
# finalize edge cases
# --------------------------------------------------------------------------- #


def test_double_finish_streaming_is_noop(conv: ConversationControl) -> None:
    conv.start_streaming("assistant")
    conv.append_streaming("only once", "text")
    conv.finish_streaming()
    conv.finish_streaming()  # must not crash or duplicate
    assistant = [c for (r, c, *_rest) in conv.messages if r == "assistant"]
    assert assistant == ["only once"]


def test_finish_empty_stream_records_empty_message(conv: ConversationControl) -> None:
    conv.start_streaming("assistant")
    conv.finish_streaming()  # empty but not None -> a (blank) assistant message
    assert conv.streaming_message is None
    assert any(r == "assistant" and c == "" for (r, c, *_rest) in conv.messages)


def test_finish_with_no_active_stream_is_noop(conv: ConversationControl) -> None:
    # No start_streaming first; streaming_message is None.
    conv.finish_streaming()
    assert conv.messages == []


# --------------------------------------------------------------------------- #
# system_info rendering (the one production change in PR-C)
# --------------------------------------------------------------------------- #


def test_system_message_stored_in_system_info(conv: ConversationControl) -> None:
    conv.add_message("system", "Model gpt-oss loaded")
    assert conv.system_info == "Model gpt-oss loaded"
    # System messages stay out of the scrollback message list.
    assert all(role != "system" for (role, *_rest) in conv.messages)


def test_system_info_is_rendered(conv: ConversationControl) -> None:
    """Previously set-but-never-shown: a system note must now appear in output."""
    conv.add_message("system", "RECOVERYNOTE: stream interrupted")
    formatted = conv.get_formatted_text()
    assert "class:system-text" in _styles_for(formatted, "RECOVERYNOTE")
    # And it is labelled so the user knows it's a system note.
    assert any("System" in text for _style, text in formatted)


def test_system_info_renders_alongside_empty_message_list(
    conv: ConversationControl,
) -> None:
    """With only a system note (no chat yet), show the note, not the empty state."""
    conv.add_message("system", "STARTUPNOTE")
    formatted = conv.get_formatted_text()
    rendered = "".join(text for _style, text in formatted)
    assert "STARTUPNOTE" in rendered
    assert "No messages yet" not in rendered


def test_empty_state_shown_without_system_info(conv: ConversationControl) -> None:
    formatted = conv.get_formatted_text()
    rendered = "".join(text for _style, text in formatted)
    assert "No messages yet" in rendered
