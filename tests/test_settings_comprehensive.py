"""
Comprehensive tests for Settings configuration.

Tests all settings fields, validation, serialization, and edge cases.
"""

import pytest
from pydantic import ValidationError

from gerdsenai_cli.config.settings import Settings


class TestSettingsBasic:
    """Basic settings tests."""

    def test_default_initialization(self):
        """Test default settings initialization."""
        settings = Settings()
        assert settings.llm_server_url == "http://localhost:11434"
        assert settings.protocol == "http"
        assert settings.llm_host == "localhost"
        assert settings.llm_port == 11434

    def test_custom_server_url(self):
        """Test custom server URL."""
        settings = Settings(llm_server_url="http://localhost:8080")
        assert "8080" in settings.llm_server_url

    def test_custom_protocol(self):
        """Test custom protocol."""
        settings = Settings(protocol="https")
        assert settings.protocol == "https"

    def test_custom_host(self):
        """Test custom host."""
        settings = Settings(llm_host="192.168.1.100")
        assert settings.llm_host == "192.168.1.100"

    def test_custom_port(self):
        """Test custom port."""
        settings = Settings(llm_port=8000)
        assert settings.llm_port == 8000


class TestSettingsTimeouts:
    """Timeout configuration tests."""

    def test_default_api_timeout(self):
        """Test default API timeout."""
        settings = Settings()
        assert settings.api_timeout == 600.0

    def test_default_health_timeout(self):
        """Test default health check timeout."""
        settings = Settings()
        assert settings.health_check_timeout == 10.0

    def test_default_model_list_timeout(self):
        """Test default model list timeout."""
        settings = Settings()
        assert settings.model_list_timeout == 30.0

    def test_default_chat_timeout(self):
        """Test default chat timeout."""
        settings = Settings()
        assert settings.chat_timeout == 600.0

    def test_default_stream_timeout(self):
        """Test default stream timeout."""
        settings = Settings()
        assert settings.stream_timeout == 600.0

    def test_custom_api_timeout(self):
        """Test custom API timeout."""
        settings = Settings(api_timeout=1200.0)
        assert settings.api_timeout == 1200.0

    def test_custom_health_timeout(self):
        """Test custom health check timeout."""
        settings = Settings(health_check_timeout=20.0)
        assert settings.health_check_timeout == 20.0

    def test_custom_model_list_timeout(self):
        """Test custom model list timeout."""
        settings = Settings(model_list_timeout=60.0)
        assert settings.model_list_timeout == 60.0

    def test_custom_chat_timeout(self):
        """Test custom chat timeout."""
        settings = Settings(chat_timeout=1800.0)
        assert settings.chat_timeout == 1800.0

    def test_custom_stream_timeout(self):
        """Test custom stream timeout."""
        settings = Settings(stream_timeout=2000.0)
        assert settings.stream_timeout == 2000.0


class TestSettingsValidation:
    """Settings validation tests."""

    def test_api_timeout_min_validation(self):
        """Test API timeout minimum validation."""
        with pytest.raises(ValidationError):
            Settings(api_timeout=0.5)

    def test_api_timeout_max_validation(self):
        """Test API timeout maximum validation."""
        with pytest.raises(ValidationError):
            Settings(api_timeout=4000.0)

    def test_health_timeout_min_validation(self):
        """Test health timeout minimum validation."""
        with pytest.raises(ValidationError):
            Settings(health_check_timeout=0.0)

    def test_health_timeout_max_validation(self):
        """Test health timeout maximum validation."""
        with pytest.raises(ValidationError):
            Settings(health_check_timeout=100.0)

    def test_model_list_timeout_min_validation(self):
        """Test model list timeout minimum validation."""
        with pytest.raises(ValidationError):
            Settings(model_list_timeout=0.5)

    def test_model_list_timeout_max_validation(self):
        """Test model list timeout maximum validation."""
        with pytest.raises(ValidationError):
            Settings(model_list_timeout=150.0)

    def test_chat_timeout_min_validation(self):
        """Test chat timeout minimum validation."""
        with pytest.raises(ValidationError):
            Settings(chat_timeout=0.0)

    def test_chat_timeout_max_validation(self):
        """Test chat timeout maximum validation."""
        with pytest.raises(ValidationError):
            Settings(chat_timeout=4000.0)

    def test_stream_timeout_min_validation(self):
        """Test stream timeout minimum validation."""
        with pytest.raises(ValidationError):
            Settings(stream_timeout=0.5)

    def test_stream_timeout_max_validation(self):
        """Test stream timeout maximum validation."""
        with pytest.raises(ValidationError):
            Settings(stream_timeout=5000.0)

    def test_port_min_validation(self):
        """Test port minimum validation."""
        with pytest.raises(ValidationError):
            Settings(llm_port=0)

    def test_port_max_validation(self):
        """Test port maximum validation."""
        with pytest.raises(ValidationError):
            Settings(llm_port=70000)

    def test_protocol_validation_http(self):
        """Test protocol validation for http."""
        settings = Settings(protocol="http")
        assert settings.protocol == "http"

    def test_protocol_validation_https(self):
        """Test protocol validation for https."""
        settings = Settings(protocol="https")
        assert settings.protocol == "https"

    def test_protocol_validation_invalid(self):
        """Test protocol validation for invalid value."""
        with pytest.raises(ValidationError):
            Settings(protocol="ftp")

    def test_protocol_case_insensitive(self):
        """Test protocol is case insensitive."""
        settings = Settings(protocol="HTTP")
        assert settings.protocol == "http"

    def test_host_validation_empty(self):
        """Test host validation for empty string."""
        with pytest.raises(ValidationError):
            Settings(llm_host="")

    def test_host_validation_whitespace(self):
        """Test host validation for whitespace."""
        with pytest.raises(ValidationError):
            Settings(llm_host="   ")


class TestSettingsContextWindow:
    """Context window configuration tests."""

    def test_default_context_window(self):
        """Test default context window."""
        settings = Settings()
        assert settings.model_context_window is None

    def test_custom_context_window(self):
        """Test custom context window."""
        settings = Settings(model_context_window=8192)
        assert settings.model_context_window == 8192

    def test_context_window_usage(self):
        """Test context window usage."""
        settings = Settings()
        assert settings.context_window_usage == 0.8

    def test_custom_context_window_usage(self):
        """Test custom context window usage."""
        settings = Settings(context_window_usage=0.9)
        assert settings.context_window_usage == 0.9

    def test_context_window_usage_min_validation(self):
        """Test context window usage minimum."""
        with pytest.raises(ValidationError):
            Settings(context_window_usage=0.0)

    def test_context_window_usage_max_validation(self):
        """Test context window usage maximum."""
        with pytest.raises(ValidationError):
            Settings(context_window_usage=1.1)


class TestSettingsSmartRouting:
    """Smart routing configuration tests."""

    def test_default_smart_routing(self):
        """Test default smart routing."""
        settings = Settings()
        assert settings.enable_smart_routing is True

    def test_disable_smart_routing(self):
        """Test disabling smart routing."""
        settings = Settings(enable_smart_routing=False)
        assert settings.enable_smart_routing is False

    def test_default_proactive_context(self):
        """Test default proactive context."""
        settings = Settings()
        assert settings.enable_proactive_context is True

    def test_disable_proactive_context(self):
        """Test disabling proactive context."""
        settings = Settings(enable_proactive_context=False)
        assert settings.enable_proactive_context is False

    def test_default_intent_confidence(self):
        """Test default intent confidence threshold."""
        settings = Settings()
        assert settings.intent_confidence_threshold == 0.85

    def test_custom_intent_confidence(self):
        """Test custom intent confidence threshold."""
        settings = Settings(intent_confidence_threshold=0.9)
        assert settings.intent_confidence_threshold == 0.9

    def test_intent_confidence_min_validation(self):
        """Test intent confidence minimum validation."""
        with pytest.raises(ValidationError):
            Settings(intent_confidence_threshold=-0.1)

    def test_intent_confidence_max_validation(self):
        """Test intent confidence maximum validation."""
        with pytest.raises(ValidationError):
            Settings(intent_confidence_threshold=1.1)

    def test_default_clarification_threshold(self):
        """Test default clarification threshold."""
        settings = Settings()
        assert settings.clarification_threshold == 0.60

    def test_custom_clarification_threshold(self):
        """Test custom clarification threshold."""
        settings = Settings(clarification_threshold=0.7)
        assert settings.clarification_threshold == 0.7


class TestSettingsUserPreferences:
    """User preferences tests."""

    def test_default_preferences(self):
        """Test default user preferences."""
        settings = Settings()
        assert "theme" in settings.user_preferences
        assert "streaming" in settings.user_preferences
        assert "tui_mode" in settings.user_preferences

    def test_get_preference(self):
        """Test getting preference."""
        settings = Settings()
        theme = settings.get_preference("theme")
        assert theme is not None

    def test_get_preference_default(self):
        """Test getting preference with default."""
        settings = Settings()
        value = settings.get_preference("nonexistent", "default_value")
        assert value == "default_value"

    def test_set_preference(self):
        """Test setting preference."""
        settings = Settings()
        settings.set_preference("test_key", "test_value")
        assert settings.get_preference("test_key") == "test_value"

    def test_custom_preferences(self):
        """Test custom user preferences."""
        custom_prefs = {"custom_key": "custom_value"}
        settings = Settings(user_preferences=custom_prefs)
        assert settings.user_preferences["custom_key"] == "custom_value"


class TestSettingsSerialization:
    """Serialization tests."""

    def test_model_dump(self):
        """Test model dump."""
        settings = Settings()
        data = settings.model_dump()
        assert isinstance(data, dict)
        assert "llm_server_url" in data
        assert "api_timeout" in data

    def test_model_dump_round_trip(self):
        """Test model dump and reconstruction."""
        settings1 = Settings(api_timeout=1200.0)
        data = settings1.model_dump()
        settings2 = Settings(**data)
        assert settings2.api_timeout == 1200.0

    def test_json_serialization(self):
        """Test JSON serialization."""
        settings = Settings()
        json_str = settings.model_dump_json()
        assert isinstance(json_str, str)
        assert "llm_server_url" in json_str


class TestSettingsURLSync:
    """URL synchronization tests."""

    def test_url_from_components(self):
        """Test URL built from components."""
        settings = Settings(
            protocol="http",
            llm_host="localhost",
            llm_port=8080,
        )
        assert "http://localhost:8080" in settings.llm_server_url

    def test_components_from_url(self):
        """Test components extracted from URL."""
        settings = Settings(llm_server_url="http://localhost:9000")
        assert settings.llm_port == 9000

    def test_url_trailing_slash_removed(self):
        """Test trailing slash is removed from URL."""
        settings = Settings(llm_server_url="http://localhost:11434/")
        assert not settings.llm_server_url.endswith("/")


class TestSettingsRetry:
    """Retry configuration tests."""

    def test_default_max_retries(self):
        """Test default max retries."""
        settings = Settings()
        assert settings.max_retries == 3

    def test_custom_max_retries(self):
        """Test custom max retries."""
        settings = Settings(max_retries=5)
        assert settings.max_retries == 5

    def test_zero_retries(self):
        """Test zero retries."""
        settings = Settings(max_retries=0)
        assert settings.max_retries == 0

    def test_max_retries_validation(self):
        """Test max retries validation."""
        with pytest.raises(ValidationError):
            Settings(max_retries=15)


class TestSettingsDebug:
    """Debug configuration tests."""

    def test_default_debug_mode(self):
        """Test default debug mode."""
        settings = Settings()
        assert settings.debug_mode is False

    def test_enable_debug_mode(self):
        """Test enabling debug mode."""
        settings = Settings(debug_mode=True)
        assert settings.debug_mode is True

    def test_default_log_level(self):
        """Test default log level."""
        settings = Settings()
        assert settings.log_level == "INFO"

    def test_custom_log_level(self):
        """Test custom log level."""
        settings = Settings(log_level="DEBUG")
        assert settings.log_level == "DEBUG"

    def test_log_level_validation(self):
        """Test log level validation."""
        with pytest.raises(ValidationError):
            Settings(log_level="INVALID")

    def test_log_level_case_insensitive(self):
        """Test log level is case insensitive."""
        settings = Settings(log_level="debug")
        assert settings.log_level == "DEBUG"


class TestSettingsFileHandling:
    """File handling configuration tests."""

    def test_default_auto_read_strategy(self):
        """Test default auto read strategy."""
        settings = Settings()
        assert settings.auto_read_strategy == "smart"

    def test_custom_auto_read_strategy(self):
        """Test custom auto read strategy."""
        settings = Settings(auto_read_strategy="whole_repo")
        assert settings.auto_read_strategy == "whole_repo"

    def test_auto_read_strategy_validation(self):
        """Test auto read strategy validation."""
        with pytest.raises(ValidationError):
            Settings(auto_read_strategy="invalid")

    def test_default_file_summarization(self):
        """Test default file summarization."""
        settings = Settings()
        assert settings.enable_file_summarization is True

    def test_disable_file_summarization(self):
        """Test disabling file summarization."""
        settings = Settings(enable_file_summarization=False)
        assert settings.enable_file_summarization is False

    def test_default_max_iterative_reads(self):
        """Test default max iterative reads."""
        settings = Settings()
        assert settings.max_iterative_reads == 10

    def test_custom_max_iterative_reads(self):
        """Test custom max iterative reads."""
        settings = Settings(max_iterative_reads=20)
        assert settings.max_iterative_reads == 20

    def test_max_iterative_reads_validation(self):
        """Test max iterative reads validation."""
        with pytest.raises(ValidationError):
            Settings(max_iterative_reads=0)


class TestSettingsMCP:
    """MCP server configuration tests."""

    def test_default_mcp_servers(self):
        """Test default MCP servers."""
        settings = Settings()
        assert settings.mcp_servers == {}

    def test_custom_mcp_servers(self):
        """Test custom MCP servers."""
        mcp_config = {
            "github": {
                "command": "gh",
                "args": ["api"],
            }
        }
        settings = Settings(mcp_servers=mcp_config)
        assert "github" in settings.mcp_servers


class TestSettingsModel:
    """Model configuration tests."""

    def test_default_current_model(self):
        """Test default current model."""
        settings = Settings()
        assert settings.current_model == ""

    def test_custom_current_model(self):
        """Test custom current model."""
        settings = Settings(current_model="llama2")
        assert settings.current_model == "llama2"

    def test_model_name_validation_strips_whitespace(self):
        """Test model name validation strips whitespace."""
        settings = Settings(current_model="  llama2  ")
        assert settings.current_model == "llama2"


class TestSettingsEdgeCases:
    """Edge case tests."""

    def test_extra_fields_allowed(self):
        """Test that extra fields are allowed."""
        settings = Settings(extra_field="extra_value")
        # Should not raise error due to extra="allow"

    def test_settings_copy(self):
        """Test settings can be copied."""
        settings1 = Settings(api_timeout=1200.0)
        data = settings1.model_dump()
        settings2 = Settings(**data)
        assert settings2.api_timeout == settings1.api_timeout

    def test_float_timeout_precision(self):
        """Test float timeout precision."""
        settings = Settings(chat_timeout=1234.567)
        assert abs(settings.chat_timeout - 1234.567) < 0.001

    def test_multiple_settings_instances(self):
        """Test multiple settings instances are independent."""
        settings1 = Settings(api_timeout=600.0)
        settings2 = Settings(api_timeout=1200.0)
        assert settings1.api_timeout != settings2.api_timeout

    def test_settings_update(self):
        """Test settings can be updated."""
        settings = Settings(api_timeout=600.0)
        settings.api_timeout = 1200.0
        assert settings.api_timeout == 1200.0
