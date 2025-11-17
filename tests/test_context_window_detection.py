"""Test context window auto-detection for Phase 8c."""

import pytest

from gerdsenai_cli.config.settings import Settings
from gerdsenai_cli.core.llm_client import LLMClient


@pytest.fixture
def llm_client():
    """Create an LLM client for testing."""
    settings = Settings()
    return LLMClient(settings)


def test_gpt_models_context_window(llm_client):
    """Test GPT model context window detection."""
    client = llm_client

    assert client.get_model_context_window("gpt-4-turbo") == 128_000
    assert client.get_model_context_window("gpt-4-1106-preview") == 128_000
    assert client.get_model_context_window("gpt-4-32k") == 32_768
    assert client.get_model_context_window("gpt-4") == 8_192
    assert client.get_model_context_window("gpt-3.5-turbo-16k") == 16_384
    assert client.get_model_context_window("gpt-3.5-turbo") == 4_096


def test_gemini_models_context_window(llm_client):
    """Test Gemini model context window detection."""
    client = llm_client

    assert client.get_model_context_window("gemini-1.5-pro") == 1_000_000
    assert client.get_model_context_window("gemini-pro") == 1_000_000
    assert client.get_model_context_window("gemini-1.0") == 32_768


def test_claude_models_context_window(llm_client):
    """Test Claude model context window detection."""
    client = llm_client

    assert client.get_model_context_window("claude-3-opus") == 200_000
    assert client.get_model_context_window("claude-3-sonnet") == 200_000
    assert client.get_model_context_window("claude-2") == 100_000
    assert client.get_model_context_window("claude") == 100_000


def test_llama_models_context_window(llm_client):
    """Test Llama model context window detection."""
    client = llm_client

    assert client.get_model_context_window("llama-3-70b") == 8_192
    assert client.get_model_context_window("llama-3-8b") == 8_192
    assert client.get_model_context_window("llama-2-13b") == 4_096
    assert client.get_model_context_window("llama") == 4_096


def test_mistral_models_context_window(llm_client):
    """Test Mistral model context window detection."""
    client = llm_client

    assert client.get_model_context_window("mixtral-8x7b") == 32_768
    assert client.get_model_context_window("mistral-7b") == 8_192
    assert client.get_model_context_window("mistral-large") == 32_768


def test_other_models_context_window(llm_client):
    """Test other model families."""
    client = llm_client

    assert client.get_model_context_window("qwen-72b") == 32_768
    assert client.get_model_context_window("qwen-7b") == 8_192
    assert client.get_model_context_window("yi-34b") == 200_000
    assert client.get_model_context_window("deepseek-coder") == 32_768
    assert client.get_model_context_window("phi-3") == 128_000
    assert client.get_model_context_window("solar-10.7b") == 4_096


def test_unknown_model_defaults(llm_client):
    """Test that unknown models default to 4096 tokens."""
    client = llm_client

    assert client.get_model_context_window("unknown-model") == 4_096
    assert client.get_model_context_window("custom-model-xyz") == 4_096


def test_case_insensitive_matching(llm_client):
    """Test that model matching is case-insensitive."""
    client = llm_client

    assert client.get_model_context_window("GPT-4-TURBO") == 128_000
    assert client.get_model_context_window("Gemini-Pro") == 1_000_000
    assert client.get_model_context_window("Claude-3-Opus") == 200_000
    assert client.get_model_context_window("LLAMA-3-70B") == 8_192


def test_context_budget_calculation(llm_client):
    """Test that context budget calculation works with different models."""
    client = llm_client

    # Gemini 1.5 Pro with 80% usage
    context_window = client.get_model_context_window("gemini-1.5-pro")
    assert context_window == 1_000_000
    max_context = int(context_window * 0.8)
    assert max_context == 800_000

    # Claude 3 with 80% usage
    context_window = client.get_model_context_window("claude-3-opus")
    assert context_window == 200_000
    max_context = int(context_window * 0.8)
    assert max_context == 160_000

    # Llama 3 with 80% usage
    context_window = client.get_model_context_window("llama-3-70b")
    assert context_window == 8_192
    max_context = int(context_window * 0.8)
    assert max_context == 6_553
