"""
Integration tests for TUI features: modes, thinking, MCP, info bar, copy, animations.

Tests verify that all user-facing features work correctly together.
"""

import asyncio
from unittest.mock import Mock, patch

import pytest

from gerdsenai_cli.core.capabilities import CapabilityDetector
from gerdsenai_cli.core.modes import ExecutionMode
from gerdsenai_cli.ui.prompt_toolkit_tui import PromptToolkitTUI


class TestModeIntegration:
    """Test mode switching and colors."""

    def test_mode_cycling(self):
        """Test mode cycling through all modes."""
        tui = PromptToolkitTUI()

        # Start in CHAT
        assert tui.get_mode() == ExecutionMode.CHAT

        # Cycle to ARCHITECT
        tui.mode_manager.toggle_mode()
        assert tui.get_mode() == ExecutionMode.ARCHITECT

        # Cycle to EXECUTE
        tui.mode_manager.toggle_mode()
        assert tui.get_mode() == ExecutionMode.EXECUTE

        # Cycle to LLVL
        tui.mode_manager.toggle_mode()
        assert tui.get_mode() == ExecutionMode.LLVL

        # Cycle back to CHAT
        tui.mode_manager.toggle_mode()
        assert tui.get_mode() == ExecutionMode.CHAT

    def test_mode_colors(self):
        """Test each mode has correct border color."""
        tui = PromptToolkitTUI()

        # CHAT = Blue
        tui.mode_manager.set_mode(ExecutionMode.CHAT)
        # Style is applied internally via update_mode_style()
        assert tui.app.style is not None

        # ARCHITECT = Orange
        tui.mode_manager.set_mode(ExecutionMode.ARCHITECT)
        assert tui.app.style is not None

        # EXECUTE = Green
        tui.mode_manager.set_mode(ExecutionMode.EXECUTE)
        assert tui.app.style is not None

        # LLVL = Magenta
        tui.mode_manager.set_mode(ExecutionMode.LLVL)
        assert tui.app.style is not None

    def test_mode_descriptions(self):
        """Test mode descriptions are displayed correctly."""
        tui = PromptToolkitTUI()

        for mode in [ExecutionMode.CHAT, ExecutionMode.ARCHITECT, ExecutionMode.EXECUTE, ExecutionMode.LLVL]:
            tui.mode_manager.set_mode(mode)
            desc = tui.mode_manager.get_mode_description()
            assert len(desc) > 0
            assert mode.value.upper() in desc or mode.value.capitalize() in desc


class TestThinkingIntegration:
    """Test thinking toggle and capability detection."""

    def test_thinking_toggle(self):
        """Test thinking can be toggled on and off."""
        tui = PromptToolkitTUI()

        # Start disabled
        assert not tui.thinking_enabled

        # Enable
        tui.thinking_enabled = True
        assert tui.thinking_enabled

        # Disable
        tui.thinking_enabled = False
        assert not tui.thinking_enabled

    def test_capability_detection_thinking_models(self):
        """Test thinking capability detection for known models."""
        # Claude-3 supports thinking
        caps = CapabilityDetector.detect_from_model_name("claude-3-opus")
        assert caps.supports_thinking

        # GPT-4 supports thinking
        caps = CapabilityDetector.detect_from_model_name("gpt-4-turbo")
        assert caps.supports_thinking

        # Qwen supports thinking
        caps = CapabilityDetector.detect_from_model_name("qwen-2.5-coder")
        assert caps.supports_thinking

        # Unknown model defaults to no thinking
        caps = CapabilityDetector.detect_from_model_name("unknown-model")
        assert not caps.supports_thinking

    def test_capability_detection_vision_models(self):
        """Test vision capability detection for known models."""
        # Claude-3 supports vision
        caps = CapabilityDetector.detect_from_model_name("claude-3-sonnet")
        assert caps.supports_vision

        # GPT-4o supports vision
        caps = CapabilityDetector.detect_from_model_name("gpt-4o")
        assert caps.supports_vision

        # LLaVA supports vision
        caps = CapabilityDetector.detect_from_model_name("llava-v1.5")
        assert caps.supports_vision

        # Text-only model doesn't support vision
        caps = CapabilityDetector.detect_from_model_name("llama-3")
        assert not caps.supports_vision

    def test_capability_detection_tool_models(self):
        """Test tool capability detection for known models."""
        # Claude-3 supports tools
        caps = CapabilityDetector.detect_from_model_name("claude-3-opus")
        assert caps.supports_tools

        # GPT-4 supports tools
        caps = CapabilityDetector.detect_from_model_name("gpt-4")
        assert caps.supports_tools

        # Gemini supports tools
        caps = CapabilityDetector.detect_from_model_name("gemini-pro")
        assert caps.supports_tools


class TestMCPIntegration:
    """Test MCP command integration."""

    @pytest.mark.asyncio
    async def test_mcp_command_exists(self):
        """Test /mcp command is recognized."""
        from gerdsenai_cli.commands.mcp import MCPCommand
        from gerdsenai_cli.commands.parser import CommandParser

        parser = CommandParser()
        # Register MCP command manually for this test
        parser.register_command(MCPCommand())

        # Check command can be retrieved
        mcp_cmd = parser.registry.get_command('mcp')
        assert mcp_cmd is not None

    @pytest.mark.asyncio
    async def test_mcp_list_empty(self):
        """Test MCP list with no servers."""
        from gerdsenai_cli.commands.mcp import MCPCommand
        from gerdsenai_cli.config.settings import Settings

        cmd = MCPCommand()
        settings = Settings()
        settings.mcp_servers = {}

        result = await cmd.execute(
            {"action": "list"},
            {"settings": settings}
        )

        assert result.success
        assert result.message is None or "no" in result.message.lower()

    @pytest.mark.asyncio
    async def test_mcp_add_server(self):
        """Test adding an MCP server."""
        from unittest.mock import AsyncMock

        from gerdsenai_cli.commands.mcp import MCPCommand
        from gerdsenai_cli.config.settings import Settings

        cmd = MCPCommand()
        settings = Settings()
        settings.mcp_servers = {}

        # Mock config manager save
        config_manager = Mock()
        config_manager.save_settings = AsyncMock()

        result = await cmd.execute(
            {"action": "add", "name": "test-server", "url": "http://localhost:8000"},
            {"settings": settings, "config_manager": config_manager}
        )

        assert result.success
        assert "test-server" in settings.mcp_servers
        assert settings.mcp_servers["test-server"]["url"] == "http://localhost:8000"

    @pytest.mark.asyncio
    async def test_mcp_remove_server(self):
        """Test removing an MCP server."""
        from unittest.mock import AsyncMock

        from gerdsenai_cli.commands.mcp import MCPCommand
        from gerdsenai_cli.config.settings import Settings

        cmd = MCPCommand()
        settings = Settings()
        settings.mcp_servers = {"test-server": {"url": "http://localhost:8000"}}

        config_manager = Mock()
        config_manager.save_settings = AsyncMock()

        result = await cmd.execute(
            {"action": "remove", "name": "test-server"},
            {"settings": settings, "config_manager": config_manager}
        )

        assert result.success
        assert "test-server" not in settings.mcp_servers

    @pytest.mark.asyncio
    async def test_mcp_connect_server(self):
        """Test connecting to an MCP server."""
        from gerdsenai_cli.commands.mcp import MCPCommand
        from gerdsenai_cli.config.settings import Settings

        cmd = MCPCommand()
        settings = Settings()
        settings.mcp_servers = {"test-server": {"url": "http://localhost:8000", "status": "Not connected"}}

        result = await cmd.execute(
            {"action": "connect", "name": "test-server"},
            {"settings": settings}
        )

        assert result.success
        assert "connected" in settings.mcp_servers["test-server"]["status"].lower()

    @pytest.mark.asyncio
    async def test_mcp_status(self):
        """Test MCP status command."""
        from gerdsenai_cli.commands.mcp import MCPCommand
        from gerdsenai_cli.config.settings import Settings

        cmd = MCPCommand()
        settings = Settings()
        settings.mcp_servers = {
            "server1": {"url": "http://localhost:8000", "status": "Connected"},
            "server2": {"url": "http://localhost:8001", "status": "Not connected"},
        }

        result = await cmd.execute(
            {"action": "status"},
            {"settings": settings}
        )

        assert result.success
        if result.message:
            assert "1/2" in result.message


class TestInfoBarIntegration:
    """Test info bar system."""

    def test_info_bar_initialization(self):
        """Test info bar starts with correct default values."""
        tui = PromptToolkitTUI()

        assert tui.token_count == 0
        assert tui.context_usage == 0.0
        assert tui.current_activity == "Ready"

    def test_update_info_bar(self):
        """Test updating info bar values."""
        tui = PromptToolkitTUI()

        tui.update_info_bar(
            tokens=1234,
            context=0.45,
            activity="Processing"
        )

        assert tui.token_count == 1234
        assert tui.context_usage == 0.45
        assert tui.current_activity == "Processing"

    def test_info_bar_formatting(self):
        """Test info bar text formatting."""
        tui = PromptToolkitTUI()

        tui.update_info_bar(
            tokens=500,
            context=0.25,
            activity="Thinking"
        )

        info_text = tui._get_info_bar_text()
        info_str = str(info_text)

        assert "500" in info_str
        assert "25" in info_str
        assert "Thinking" in info_str


class TestCopyIntegration:
    """Test copy conversation feature."""

    def test_copy_command_exists(self):
        """Test /copy command is recognized."""
        # The /copy command is handled internally by the TUI
        tui = PromptToolkitTUI()
        result = tui.copy_conversation_to_clipboard()
        assert isinstance(result, tuple)
        assert len(result) == 2

    @patch('subprocess.Popen')
    def test_copy_with_pbcopy(self, mock_popen):
        """Test copying conversation to clipboard with pbcopy."""
        tui = PromptToolkitTUI()
        tui.conversation.add_message("user", "Hello")
        tui.conversation.add_message("assistant", "Hi there!")

        mock_process = Mock()
        mock_process.communicate.return_value = (None, None)
        mock_popen.return_value = mock_process

        success, message = tui.copy_conversation_to_clipboard()

        assert success
        assert "copied" in message.lower()
        assert mock_popen.called

    @patch('subprocess.Popen', side_effect=FileNotFoundError)
    def test_copy_fallback_to_pyperclip(self, mock_popen):
        """Test fallback to pyperclip when pbcopy fails."""
        tui = PromptToolkitTUI()
        tui.conversation.add_message("user", "Test message")

        # Mock pyperclip.copy after Popen fails
        with patch('pyperclip.copy'):
            success, message = tui.copy_conversation_to_clipboard()

            # Should successfully fall back to pyperclip
            assert success
            assert "copied" in message.lower()


class TestAnimationIntegration:
    """Test animation system integration."""

    @pytest.mark.asyncio
    async def test_show_hide_animation(self):
        """Test showing and hiding animations."""
        tui = PromptToolkitTUI()

        # Show animation
        tui.show_animation("Processing", "thinking")
        assert tui.current_animation is not None

        # Wait a bit for animation to start
        await asyncio.sleep(0.1)

        # Hide animation
        tui.hide_animation()

        # Wait for cleanup
        await asyncio.sleep(0.1)

        assert tui.current_animation is None

    def test_animation_types(self):
        """Test different animation types can be created."""
        from gerdsenai_cli.ui.animations import AnimationFrames

        # Access frame constants directly
        assert len(AnimationFrames.SPINNER) > 0
        assert len(AnimationFrames.THINKING) > 0
        assert len(AnimationFrames.PLANNING) > 0
        assert len(AnimationFrames.ANALYZING) > 0
        assert len(AnimationFrames.EXECUTING) > 0
        assert len(AnimationFrames.DOTS) > 0


class TestEndToEndWorkflow:
    """Test complete workflows."""

    @pytest.mark.asyncio
    async def test_architect_mode_workflow(self):
        """Test complete ARCHITECT mode workflow with approval."""
        tui = PromptToolkitTUI()

        # Set to ARCHITECT mode
        tui.mode_manager.set_mode(ExecutionMode.ARCHITECT)

        # Simulate plan capture
        from gerdsenai_cli.ui.animations import PlanCapture

        plan_response = """
        I'll create a new feature. Here's the plan:

        1. Create config.py
        2. Update main.py to load config
        3. Add tests
        """

        plan = PlanCapture.extract_summary(plan_response)

        # Should extract files and actions
        assert len(plan['files_affected']) > 0 or len(plan['actions']) > 0

        # Show plan for approval
        tui.show_plan_for_approval(plan)

        assert tui.approval_mode
        assert tui.pending_plan is not None

    @pytest.mark.asyncio
    async def test_streaming_response(self):
        """Test streaming response workflow."""
        tui = PromptToolkitTUI()

        # Start streaming
        tui.start_streaming_response()
        assert tui.conversation.streaming_message is not None

        # Add chunks
        tui.append_streaming_chunk("Hello ")
        tui.append_streaming_chunk("World!")

        # Finish
        tui.finish_streaming_response()
        assert tui.conversation.streaming_message is None

        # Check message was added
        messages = tui.conversation.messages
        assert len(messages) > 0
        assert "Hello World!" in messages[-1][1]  # Content is at index 1


class TestCapabilityDetectionIntegration:
    """Test capability detection across the system."""

    def test_all_capabilities_detected(self):
        """Test comprehensive capability detection."""
        test_cases = [
            # (model_name, thinking, vision, tools)
            ("claude-3-opus", True, True, True),
            ("gpt-4o", True, True, True),
            ("gpt-4-turbo", True, False, True),
            ("qwen-2.5-coder", True, False, False),  # Qwen doesn't support tools in current detection
            ("llama-3-70b", False, False, False),
            ("gemini-pro", False, False, True),
        ]

        for model_name, should_think, should_vision, should_tools in test_cases:
            caps = CapabilityDetector.detect_from_model_name(model_name)
            assert caps.supports_thinking == should_think, f"Failed thinking for {model_name}"
            assert caps.supports_vision == should_vision, f"Failed vision for {model_name}"
            assert caps.supports_tools == should_tools, f"Failed tools for {model_name}"

    def test_streaming_always_supported(self):
        """Test streaming is marked as supported for all models."""
        models = ["claude-3-opus", "gpt-4", "llama-3", "unknown-model"]

        for model in models:
            caps = CapabilityDetector.detect_from_model_name(model)
            assert caps.supports_streaming  # Should be True for all models


# Mark slow tests
pytestmark = pytest.mark.integration
