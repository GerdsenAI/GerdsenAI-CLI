"""
Test Phase 8c: Dynamic Context Building

Tests the new dynamic context building features including:
- Context window auto-detection
- Token-aware context building
- File prioritization
- Summarization strategies
"""

import asyncio
from pathlib import Path

import pytest

from gerdsenai_cli.config.settings import Settings
from gerdsenai_cli.core.context_manager import ProjectContext
from gerdsenai_cli.core.llm_client import LLMClient


class TestContextWindowDetection:
    """Test context window auto-detection for various models."""

    def test_gpt4_turbo_detection(self):
        """Test GPT-4 Turbo context window detection."""
        settings = Settings(llm_server_url="http://localhost:11434", current_model="test")
        client = LLMClient(settings=settings)

        assert client.get_model_context_window("gpt-4-turbo") == 128000
        assert client.get_model_context_window("gpt-4-turbo-preview") == 128000
        assert client.get_model_context_window("gpt-4-1106-preview") == 128000

    def test_gemini_detection(self):
        """Test Gemini Pro context window detection."""
        settings = Settings(llm_server_url="http://localhost:11434", current_model="test")
        client = LLMClient(settings=settings)

        assert client.get_model_context_window("gemini-pro") == 1000000
        assert client.get_model_context_window("gemini-1.5-pro") == 1000000

    def test_claude3_detection(self):
        """Test Claude 3 context window detection."""
        settings = Settings(llm_server_url="http://localhost:11434", current_model="test")
        client = LLMClient(settings=settings)

        assert client.get_model_context_window("claude-3-opus") == 200000
        assert client.get_model_context_window("claude-3-sonnet") == 200000

    def test_llama3_detection(self):
        """Test Llama 3 context window detection."""
        settings = Settings(llm_server_url="http://localhost:11434", current_model="test")
        client = LLMClient(settings=settings)

        assert client.get_model_context_window("llama3") == 8192
        assert client.get_model_context_window("llama-3-8b") == 8192

    def test_unknown_model_fallback(self):
        """Test fallback to 4K for unknown models."""
        settings = Settings(llm_server_url="http://localhost:11434", current_model="test")
        client = LLMClient(settings=settings)

        assert client.get_model_context_window("unknown-model-xyz") == 4096


class TestDynamicSettings:
    """Test Phase 8c settings validation."""

    def test_context_window_usage_validation(self):
        """Test context window usage percentage validation."""
        settings = Settings(
            llm_server_url="http://localhost:11434",
            current_model="test-model",
            context_window_usage=0.8
        )
        assert settings.context_window_usage == 0.8

    def test_auto_read_strategy_validation(self):
        """Test auto-read strategy validation."""
        # Valid strategies
        for strategy in ["smart", "whole_repo", "iterative", "off"]:
            settings = Settings(
                llm_server_url="http://localhost:11434",
                current_model="test-model",
                auto_read_strategy=strategy
            )
            assert settings.auto_read_strategy == strategy

    def test_file_summarization_default(self):
        """Test file summarization is enabled by default."""
        settings = Settings(
            llm_server_url="http://localhost:11434",
            current_model="test-model"
        )
        assert settings.enable_file_summarization is True


class TestTokenEstimation:
    """Test token estimation functionality."""

    def test_estimate_tokens(self):
        """Test token estimation accuracy."""
        # Rule: ~4 characters per token
        text = "a" * 400  # 400 chars = ~100 tokens
        estimated = ProjectContext._estimate_tokens(text)
        # Allow small variance due to tiktoken encoding
        assert 95 <= estimated <= 105

    def test_estimate_tokens_empty(self):
        """Test token estimation with empty string."""
        estimated = ProjectContext._estimate_tokens("")
        assert estimated == 0


@pytest.mark.asyncio
class TestDynamicContextBuilding:
    """Test dynamic context building strategies."""

    async def test_smart_strategy_integration(self):
        """Test smart context building strategy."""
        context_manager = ProjectContext(project_root=Path.cwd())

        # Scan current project
        await context_manager.scan_directory(max_depth=2)

        # Build context with smart strategy
        context = await context_manager.build_dynamic_context(
            query="test",
            max_tokens=1000,
            strategy="smart"
        )

        assert context is not None
        assert isinstance(context, str)
        assert len(context) > 0

    async def test_off_strategy_returns_empty(self):
        """Test 'off' strategy returns empty context."""
        context_manager = ProjectContext(project_root=Path.cwd())

        context = await context_manager.build_dynamic_context(
            query="test",
            max_tokens=1000,
            strategy="off"
        )

        assert context == ""

    async def test_file_prioritization(self):
        """Test file prioritization logic."""
        context_manager = ProjectContext(project_root=Path.cwd())
        await context_manager.scan_directory(max_depth=2)

        # Prioritize files with mentioned file
        mentioned_files = [Path("README.md")]
        prioritized = context_manager._prioritize_files(
            query="readme",
            mentioned_files=mentioned_files
        )

        # Mentioned files should be first
        assert len(prioritized) > 0
        # README.md should be highly prioritized
        readme_files = [f for f in prioritized if f.path.name.lower() == "readme.md"]
        assert len(readme_files) > 0

    async def test_summarization_strategy(self):
        """Test file summarization strategy."""
        context_manager = ProjectContext(project_root=Path.cwd())

        # Create long content
        long_content = "line\n" * 1000  # 1000 lines

        # Summarize to fit 200 tokens
        summarized = await context_manager._summarize_file(long_content, max_tokens=200)

        assert len(summarized) < len(long_content)
        assert "lines omitted" in summarized or "truncated" in summarized


def test_phase8c_summary():
    """Summary test to verify Phase 8c components are present."""
    # Verify LLMClient has context window detection
    assert hasattr(LLMClient, "get_model_context_window")

    # Verify Settings has Phase 8c fields
    settings = Settings(llm_server_url="http://localhost:11434", current_model="test")
    assert hasattr(settings, "model_context_window")
    assert hasattr(settings, "context_window_usage")
    assert hasattr(settings, "auto_read_strategy")
    assert hasattr(settings, "enable_file_summarization")
    assert hasattr(settings, "max_iterative_reads")

    # Verify ProjectContext has dynamic context methods
    assert hasattr(ProjectContext, "build_dynamic_context")
    assert hasattr(ProjectContext, "_smart_context_building")
    assert hasattr(ProjectContext, "_prioritize_files")
    assert hasattr(ProjectContext, "_estimate_tokens")
    assert hasattr(ProjectContext, "_summarize_file")

    print("✅ Phase 8c implementation verified!")


if __name__ == "__main__":
    # Run summary test
    test_phase8c_summary()

    # Run async tests
    async def run_async_tests():
        test = TestDynamicContextBuilding()
        await test.test_smart_strategy_integration()
        await test.test_off_strategy_returns_empty()
        await test.test_file_prioritization()
        await test.test_summarization_strategy()
        print("✅ All async tests passed!")

    asyncio.run(run_async_tests())
