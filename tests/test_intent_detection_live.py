"""
Live Integration Tests for Phase 8b LLM-Based Intent Detection.

Tests the intent detection system with a real local LLM (e.g., LMStudio).
"""

import time
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any

import pytest
import pytest_asyncio

# Import GerdsenAI CLI components
from gerdsenai_cli.config.settings import Settings
from gerdsenai_cli.core.agent import ActionType, IntentParser
from gerdsenai_cli.core.llm_client import LLMClient

# Configure pytest-asyncio fixtures for function scope


@pytest_asyncio.fixture
async def llm_client(llm_config: dict[str, Any]) -> AsyncGenerator[LLMClient, None]:
    """Create LLM client connected to configured local server."""
    # Create settings using llm_config from conftest.py
    settings = Settings(
        protocol=llm_config["protocol"],
        llm_host=llm_config["host"],
        llm_port=llm_config["port"],
        current_model=llm_config["model"],  # Use specified model or empty string
        api_timeout=llm_config["timeout"],
    )

    # Debug: Print the constructed URL
    print(f"\n[DEBUG] Settings.llm_server_url: {settings.llm_server_url}")
    print(f"[DEBUG] Settings.protocol: {settings.protocol}")
    print(f"[DEBUG] Settings.llm_host: {settings.llm_host}")
    print(f"[DEBUG] Settings.llm_port: {settings.llm_port}")

    async with LLMClient(settings) as client:

        # Debug: Print what LLMClient will use
        print(f"[DEBUG] LLMClient.base_url: {client.base_url}")

        # Test connection
        connected = await client.connect()
        if not connected:
            pytest.skip("LLM server not available (is LMStudio running?)")

        # List and select model
        models = await client.list_models()
        if not models:
            pytest.skip("No models available in LMStudio")

        # Prefer Mistral Small if available, otherwise use first model
        preferred_models = ["mistral", "magistral", "llama", "qwen"]
        selected_model = None

        for preferred in preferred_models:
            for model in models:
                if preferred.lower() in model.id.lower():
                    selected_model = model.id
                    break
            if selected_model:
                break

        if not selected_model:
            selected_model = models[0].id

        # Update settings with selected model (only if not already set)
        if not settings.current_model:
            settings.current_model = selected_model
            print(f"\n[TEST] Auto-selected model: {selected_model}")
        else:
            print(f"\n[TEST] Using configured model: {settings.current_model}")

        yield client


@pytest.fixture
def intent_parser() -> IntentParser:
    """Create intent parser instance."""
    return IntentParser()


@pytest.fixture
def project_files() -> list[str]:
    """Get list of project files for context."""
    project_root = Path(__file__).parent.parent
    files = []

    for py_file in project_root.rglob("*.py"):
        rel_path = py_file.relative_to(project_root)
        files.append(str(rel_path))

    return files[:100]  # Limit to 100 for performance


class TestIntentDetectionLive:
    """Live integration tests for intent detection with real LLM."""

    async def test_file_reading_intent_explicit(
        self, llm_client: LLMClient, intent_parser: IntentParser, project_files: list[str]
    ) -> None:
        """Test: 'explain agent.py' should detect read_file intent."""
        query = "explain agent.py"

        start_time = time.time()
        intent = await intent_parser.detect_intent_with_llm(
            llm_client=llm_client,
            user_query=query,
            project_files=project_files
        )
        duration = time.time() - start_time

        print(f"\n[TEST] Query: '{query}'")
        print(f"[TEST] Intent: {intent.action_type.value}")
        print(f"[TEST] Confidence: {intent.confidence:.2f}")
        print(f"[TEST] Duration: {duration:.2f}s")
        print(f"[TEST] Reasoning: {intent.reasoning}")

        # Assertions
        assert intent.action_type == ActionType.READ_FILE, \
            f"Expected READ_FILE, got {intent.action_type.value}"
        assert intent.confidence >= 0.5, \
            f"Confidence too low: {intent.confidence}"
        assert duration < 15.0, \
            f"Response too slow: {duration}s"

        # Check file path extraction
        if intent.parameters.get("file_path"):
            print(f"[TEST] Extracted file: {intent.parameters['file_path']}")

    async def test_file_reading_intent_show(
        self, llm_client: LLMClient, intent_parser: IntentParser, project_files: list[str]
    ) -> None:
        """Test: 'show me main.py' should detect read_file intent."""
        query = "show me main.py"

        start_time = time.time()
        intent = await intent_parser.detect_intent_with_llm(
            llm_client=llm_client,
            user_query=query,
            project_files=project_files
        )
        duration = time.time() - start_time

        print(f"\n[TEST] Query: '{query}'")
        print(f"[TEST] Intent: {intent.action_type.value}")
        print(f"[TEST] Confidence: {intent.confidence:.2f}")
        print(f"[TEST] Duration: {duration:.2f}s")

        assert intent.action_type == ActionType.READ_FILE
        assert intent.confidence >= 0.5


    async def test_file_reading_intent_whats_in(
        self, llm_client: LLMClient, intent_parser: IntentParser, project_files: list[str]
    ) -> None:
        """Test: 'what's in llm_client.py' should detect read_file intent."""
        query = "what's in llm_client.py"

        start_time = time.time()
        intent = await intent_parser.detect_intent_with_llm(
            llm_client=llm_client,
            user_query=query,
            project_files=project_files
        )
        duration = time.time() - start_time

        print(f"\n[TEST] Query: '{query}'")
        print(f"[TEST] Intent: {intent.action_type.value}")
        print(f"[TEST] Confidence: {intent.confidence:.2f}")
        print(f"[TEST] Duration: {duration:.2f}s")

        assert intent.action_type == ActionType.READ_FILE
        assert intent.confidence >= 0.5


    async def test_project_analysis_intent_analyze(
        self, llm_client: LLMClient, intent_parser: IntentParser, project_files: list[str]
    ) -> None:
        """Test: 'analyze this project' should detect analyze_project intent."""
        query = "analyze this project"

        start_time = time.time()
        intent = await intent_parser.detect_intent_with_llm(
            llm_client=llm_client,
            user_query=query,
            project_files=project_files
        )
        duration = time.time() - start_time

        print(f"\n[TEST] Query: '{query}'")
        print(f"[TEST] Intent: {intent.action_type.value}")
        print(f"[TEST] Confidence: {intent.confidence:.2f}")
        print(f"[TEST] Duration: {duration:.2f}s")

        assert intent.action_type == ActionType.ANALYZE_PROJECT
        assert intent.confidence >= 0.5


    async def test_project_analysis_intent_overview(
        self, llm_client: LLMClient, intent_parser: IntentParser, project_files: list[str]
    ) -> None:
        """Test: 'give me an overview' should detect analyze_project intent."""
        query = "give me an overview of this codebase"

        start_time = time.time()
        intent = await intent_parser.detect_intent_with_llm(
            llm_client=llm_client,
            user_query=query,
            project_files=project_files
        )
        duration = time.time() - start_time

        print(f"\n[TEST] Query: '{query}'")
        print(f"[TEST] Intent: {intent.action_type.value}")
        print(f"[TEST] Confidence: {intent.confidence:.2f}")
        print(f"[TEST] Duration: {duration:.2f}s")

        assert intent.action_type == ActionType.ANALYZE_PROJECT
        assert intent.confidence >= 0.5


    async def test_search_intent_where(
        self, llm_client: LLMClient, intent_parser: IntentParser, project_files: list[str]
    ) -> None:
        """Test: 'where is error handling' should detect search_files intent."""
        query = "where is error handling"

        start_time = time.time()
        intent = await intent_parser.detect_intent_with_llm(
            llm_client=llm_client,
            user_query=query,
            project_files=project_files
        )
        duration = time.time() - start_time

        print(f"\n[TEST] Query: '{query}'")
        print(f"[TEST] Intent: {intent.action_type.value}")
        print(f"[TEST] Confidence: {intent.confidence:.2f}")
        print(f"[TEST] Duration: {duration:.2f}s")

        assert intent.action_type == ActionType.SEARCH_FILES
        assert intent.confidence >= 0.5


    async def test_search_intent_find(
        self, llm_client: LLMClient, intent_parser: IntentParser, project_files: list[str]
    ) -> None:
        """Test: 'find llm_client' should detect search_files intent."""
        query = "find files with llm_client"

        start_time = time.time()
        intent = await intent_parser.detect_intent_with_llm(
            llm_client=llm_client,
            user_query=query,
            project_files=project_files
        )
        duration = time.time() - start_time

        print(f"\n[TEST] Query: '{query}'")
        print(f"[TEST] Intent: {intent.action_type.value}")
        print(f"[TEST] Confidence: {intent.confidence:.2f}")
        print(f"[TEST] Duration: {duration:.2f}s")

        assert intent.action_type == ActionType.SEARCH_FILES
        assert intent.confidence >= 0.5


    async def test_chat_intent_greeting(
        self, llm_client: LLMClient, intent_parser: IntentParser, project_files: list[str]
    ) -> None:
        """Test: 'hello' should detect chat intent."""
        query = "hello how are you"

        start_time = time.time()
        intent = await intent_parser.detect_intent_with_llm(
            llm_client=llm_client,
            user_query=query,
            project_files=project_files
        )
        duration = time.time() - start_time

        print(f"\n[TEST] Query: '{query}'")
        print(f"[TEST] Intent: {intent.action_type.value}")
        print(f"[TEST] Confidence: {intent.confidence:.2f}")
        print(f"[TEST] Duration: {duration:.2f}s")

        assert intent.action_type == ActionType.CHAT
        assert intent.confidence >= 0.5


    async def test_chat_intent_capabilities(
        self, llm_client: LLMClient, intent_parser: IntentParser, project_files: list[str]
    ) -> None:
        """Test: 'what can you do' should detect chat intent."""
        query = "what can you do"

        start_time = time.time()
        intent = await intent_parser.detect_intent_with_llm(
            llm_client=llm_client,
            user_query=query,
            project_files=project_files
        )
        duration = time.time() - start_time

        print(f"\n[TEST] Query: '{query}'")
        print(f"[TEST] Intent: {intent.action_type.value}")
        print(f"[TEST] Confidence: {intent.confidence:.2f}")
        print(f"[TEST] Duration: {duration:.2f}s")

        assert intent.action_type == ActionType.CHAT
        assert intent.confidence >= 0.5


    async def test_timeout_handling(
        self, llm_client: LLMClient, intent_parser: IntentParser, project_files: list[str]
    ) -> None:
        """Test that timeout handling works gracefully."""
        query = "explain agent.py"

        # This test just ensures no crashes on timeout
        # Actual timeout is handled in detect_intent_with_llm
        try:
            intent = await intent_parser.detect_intent_with_llm(
                llm_client=llm_client,
                user_query=query,
                project_files=project_files
            )

            print("\n[TEST] Timeout test completed")
            print(f"[TEST] Intent: {intent.action_type.value}")

            # Should get some intent (either from LLM or fallback)
            assert intent.action_type != ActionType.NONE or \
                   (intent.reasoning and "timeout" in intent.reasoning.lower())

        except Exception as e:
            pytest.fail(f"Timeout handling crashed: {e}")


    async def test_file_path_extraction(
        self, llm_client: LLMClient, intent_parser: IntentParser, project_files: list[str]
    ) -> None:
        """Test file path extraction and validation."""
        query = "explain gerdsenai_cli/core/agent.py"

        intent = await intent_parser.detect_intent_with_llm(
            llm_client=llm_client,
            user_query=query,
            project_files=project_files
        )

        print("\n[TEST] File path extraction test")
        print(f"[TEST] Query: '{query}'")
        print(f"[TEST] Detected files: {intent.parameters.get('files', [])}")

        # Should have extracted at least one file
        assert "file_path" in intent.parameters or "files" in intent.parameters


# Summary test that runs all and generates report

async def test_generate_summary_report(tmp_path: Path) -> None:
    """Generate a summary report of all test results."""
    # This will be called after all tests run
    # pytest will handle the actual summary
    pass


if __name__ == "__main__":
    """Run tests directly with pytest."""
    import sys

    sys.exit(pytest.main([__file__, "-v", "-s"]))
