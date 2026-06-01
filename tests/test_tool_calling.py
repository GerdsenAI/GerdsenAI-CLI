"""Phase 1: native tool-calling in the LLM client.

Covers the wire payload (plain requests stay clean; tool requests carry the
schema), and parsing an OpenAI-shape response into text + tool calls — including
the quirks (arguments as a JSON string, missing tool_calls, bad JSON).
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from gerdsenai_cli.config.settings import Settings
from gerdsenai_cli.core.llm_client import (
    ChatCompletionRequest,
    ChatMessage,
    ChatResult,
    LLMClient,
    ToolCall,
)

_WEATHER_TOOL = {
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "Get weather for a city",
        "parameters": {
            "type": "object",
            "properties": {"city": {"type": "string"}},
            "required": ["city"],
        },
    },
}


# --------------------------------------------------------------------------- #
# wire payload
# --------------------------------------------------------------------------- #


def test_plain_request_payload_has_no_tool_keys() -> None:
    """A tool-less request serializes exactly as before (no new keys leak)."""
    req = ChatCompletionRequest(
        model="m", messages=[ChatMessage(role="user", content="hi")]
    )
    payload = req.to_payload()
    assert "tools" not in payload
    assert payload["messages"] == [{"role": "user", "content": "hi"}]
    assert "tool_calls" not in payload["messages"][0]
    assert "tool_call_id" not in payload["messages"][0]


def test_tool_request_payload_includes_tools() -> None:
    req = ChatCompletionRequest(
        model="m",
        messages=[ChatMessage(role="user", content="weather in Paris?")],
        tools=[_WEATHER_TOOL],
    )
    payload = req.to_payload()
    assert payload["tools"] == [_WEATHER_TOOL]


def test_tool_result_message_roundtrips_in_payload() -> None:
    """A tool-result message keeps its tool_call_id on the wire."""
    req = ChatCompletionRequest(
        model="m",
        messages=[
            ChatMessage(role="user", content="weather?"),
            ChatMessage(
                role="assistant",
                content="",
                tool_calls=[{"id": "c1", "function": {"name": "get_weather"}}],
            ),
            ChatMessage(role="tool", content="sunny", tool_call_id="c1"),
        ],
    )
    payload = req.to_payload()
    assistant_msg = payload["messages"][1]
    tool_msg = payload["messages"][2]
    assert assistant_msg["tool_calls"][0]["id"] == "c1"
    assert tool_msg["tool_call_id"] == "c1"
    # The plain user message stays clean.
    assert "tool_calls" not in payload["messages"][0]


# --------------------------------------------------------------------------- #
# response parsing
# --------------------------------------------------------------------------- #


def test_parse_tool_calls_with_json_string_arguments() -> None:
    """OpenAI returns arguments as a JSON STRING; we parse it to a dict."""
    data = {
        "choices": [
            {
                "message": {
                    "content": "",
                    "tool_calls": [
                        {
                            "id": "call_abc",
                            "function": {
                                "name": "get_weather",
                                "arguments": '{"city": "Paris"}',
                            },
                        }
                    ],
                }
            }
        ]
    }
    result = LLMClient._parse_tool_calls(data)
    assert result.has_tool_calls
    assert result.tool_calls[0] == ToolCall(
        id="call_abc", name="get_weather", arguments={"city": "Paris"}
    )


def test_parse_tool_calls_with_dict_arguments() -> None:
    """Some providers already give a dict; accept it as-is."""
    data = {
        "choices": [
            {
                "message": {
                    "content": "",
                    "tool_calls": [
                        {
                            "id": "c1",
                            "function": {
                                "name": "f",
                                "arguments": {"x": 1},
                            },
                        }
                    ],
                }
            }
        ]
    }
    result = LLMClient._parse_tool_calls(data)
    assert result.tool_calls[0].arguments == {"x": 1}


def test_parse_tool_calls_bad_json_arguments_is_empty_dict() -> None:
    data = {
        "choices": [
            {
                "message": {
                    "content": "",
                    "tool_calls": [
                        {
                            "id": "c1",
                            "function": {"name": "f", "arguments": "{not json"},
                        }
                    ],
                }
            }
        ]
    }
    result = LLMClient._parse_tool_calls(data)
    assert result.tool_calls[0].arguments == {}


def test_parse_plain_text_response_no_tool_calls() -> None:
    data = {"choices": [{"message": {"content": "just text"}}]}
    result = LLMClient._parse_tool_calls(data)
    assert result.content == "just text"
    assert not result.has_tool_calls


def test_parse_missing_id_gets_synthetic_id() -> None:
    data = {
        "choices": [
            {"message": {"content": "", "tool_calls": [{"function": {"name": "f"}}]}}
        ]
    }
    result = LLMClient._parse_tool_calls(data)
    assert result.tool_calls[0].id  # non-empty synthetic id


# --------------------------------------------------------------------------- #
# end-to-end via mocked HTTP
# --------------------------------------------------------------------------- #


@pytest.fixture
def client() -> LLMClient:
    import asyncio

    settings = MagicMock(spec=Settings)
    settings.llm_server_url = "http://localhost:11434"
    settings.current_model = "qwen2.5-coder"
    c = LLMClient(settings)
    asyncio.run(c.__aenter__())
    return c


@pytest.mark.asyncio
async def test_chat_with_tools_returns_tool_call(client: LLMClient) -> None:
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.raise_for_status.return_value = None
    mock_resp.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": "",
                    "tool_calls": [
                        {
                            "id": "call_1",
                            "function": {
                                "name": "get_weather",
                                "arguments": '{"city": "Paris"}',
                            },
                        }
                    ],
                }
            }
        ]
    }
    with patch.object(client.client, "post", return_value=mock_resp) as mock_post:
        result = await client.chat_with_tools(
            [ChatMessage(role="user", content="weather in Paris?")],
            tools=[_WEATHER_TOOL],
            model="qwen2.5-coder",
        )
    assert isinstance(result, ChatResult)
    assert result.tool_calls[0].name == "get_weather"
    assert result.tool_calls[0].arguments == {"city": "Paris"}
    # The tools schema was actually sent on the wire.
    sent = mock_post.call_args.kwargs["json"]
    assert sent["tools"] == [_WEATHER_TOOL]


@pytest.mark.asyncio
async def test_chat_with_tools_failure_returns_empty_result(client: LLMClient) -> None:
    from httpx import ConnectError

    with (
        patch.object(client.client, "post", side_effect=ConnectError("down")),
        patch("gerdsenai_cli.core.llm_client.show_error"),
    ):
        result = await client.chat_with_tools(
            [ChatMessage(role="user", content="hi")],
            tools=[_WEATHER_TOOL],
            model="m",
        )
    assert isinstance(result, ChatResult)
    assert not result.has_tool_calls
    assert result.content == ""


def _noop(*_a: Any, **_k: Any) -> None:
    return None
