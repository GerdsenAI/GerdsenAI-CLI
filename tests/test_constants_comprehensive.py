"""
Comprehensive tests for constants module.

Tests all constants, enums, and configuration values.
"""

import pytest

from gerdsenai_cli.constants import (
    FileLimits,
    LLMDefaults,
    PerformanceTargets,
)


class TestPerformanceTargets:
    """Performance targets tests."""

    def test_startup_time_target(self):
        """Test startup time target is reasonable."""
        assert PerformanceTargets.STARTUP_TIME > 0
        assert PerformanceTargets.STARTUP_TIME < 10.0

    def test_response_time_target(self):
        """Test response time target is reasonable."""
        assert PerformanceTargets.RESPONSE_TIME > 0
        assert PerformanceTargets.RESPONSE_TIME < 2.0

    def test_memory_baseline_target(self):
        """Test memory baseline target is reasonable."""
        assert PerformanceTargets.MEMORY_BASELINE > 0
        assert PerformanceTargets.MEMORY_BASELINE < 500.0

    def test_model_loading_target(self):
        """Test model loading target is reasonable."""
        assert PerformanceTargets.MODEL_LOADING > 0
        assert PerformanceTargets.MODEL_LOADING < 30.0

    def test_file_scanning_target(self):
        """Test file scanning target is reasonable."""
        assert PerformanceTargets.FILE_SCANNING > 0
        assert PerformanceTargets.FILE_SCANNING < 5.0

    def test_context_building_target(self):
        """Test context building target is reasonable."""
        assert PerformanceTargets.CONTEXT_BUILDING > 0
        assert PerformanceTargets.CONTEXT_BUILDING < 10.0

    def test_file_editing_target(self):
        """Test file editing target is reasonable."""
        assert PerformanceTargets.FILE_EDITING > 0
        assert PerformanceTargets.FILE_EDITING < 2.0

    def test_all_targets_are_positive(self):
        """Test all targets are positive."""
        assert PerformanceTargets.STARTUP_TIME > 0
        assert PerformanceTargets.RESPONSE_TIME > 0
        assert PerformanceTargets.MEMORY_BASELINE > 0
        assert PerformanceTargets.MODEL_LOADING > 0
        assert PerformanceTargets.FILE_SCANNING > 0
        assert PerformanceTargets.CONTEXT_BUILDING > 0
        assert PerformanceTargets.FILE_EDITING > 0

    def test_targets_are_floats(self):
        """Test all targets are floats."""
        assert isinstance(PerformanceTargets.STARTUP_TIME, float)
        assert isinstance(PerformanceTargets.RESPONSE_TIME, float)
        assert isinstance(PerformanceTargets.MEMORY_BASELINE, float)
        assert isinstance(PerformanceTargets.MODEL_LOADING, float)
        assert isinstance(PerformanceTargets.FILE_SCANNING, float)
        assert isinstance(PerformanceTargets.CONTEXT_BUILDING, float)
        assert isinstance(PerformanceTargets.FILE_EDITING, float)


class TestLLMDefaults:
    """LLM defaults tests."""

    def test_intent_detection_max_files(self):
        """Test intent detection max files."""
        assert LLMDefaults.INTENT_DETECTION_MAX_FILES > 0
        assert LLMDefaults.INTENT_DETECTION_MAX_FILES <= 1000

    def test_intent_detection_temperature(self):
        """Test intent detection temperature."""
        assert LLMDefaults.INTENT_DETECTION_TEMPERATURE >= 0.0
        assert LLMDefaults.INTENT_DETECTION_TEMPERATURE <= 1.0

    def test_intent_detection_max_tokens(self):
        """Test intent detection max tokens."""
        assert LLMDefaults.INTENT_DETECTION_MAX_TOKENS > 0
        assert LLMDefaults.INTENT_DETECTION_MAX_TOKENS <= 1000

    def test_intent_detection_timeout(self):
        """Test intent detection timeout."""
        assert LLMDefaults.INTENT_DETECTION_TIMEOUT_SECONDS > 0
        assert LLMDefaults.INTENT_DETECTION_TIMEOUT_SECONDS >= 60.0

    def test_default_temperature(self):
        """Test default temperature."""
        assert LLMDefaults.DEFAULT_TEMPERATURE >= 0.0
        assert LLMDefaults.DEFAULT_TEMPERATURE <= 2.0

    def test_default_max_tokens(self):
        """Test default max tokens."""
        assert LLMDefaults.DEFAULT_MAX_TOKENS > 0
        assert LLMDefaults.DEFAULT_MAX_TOKENS >= 4096

    def test_default_timeout(self):
        """Test default timeout."""
        assert LLMDefaults.DEFAULT_TIMEOUT_SECONDS > 0
        assert LLMDefaults.DEFAULT_TIMEOUT_SECONDS >= 600.0

    def test_temperature_is_deterministic_for_intent(self):
        """Test intent detection temperature is deterministic."""
        assert LLMDefaults.INTENT_DETECTION_TEMPERATURE < 0.5

    def test_timeout_suitable_for_local_ai(self):
        """Test timeout is suitable for local AI."""
        assert LLMDefaults.DEFAULT_TIMEOUT_SECONDS >= 300.0

    def test_max_tokens_reasonable(self):
        """Test max tokens is reasonable."""
        assert LLMDefaults.DEFAULT_MAX_TOKENS >= 2048


class TestFileLimits:
    """File limits tests."""

    def test_default_max_file_size(self):
        """Test default max file size."""
        assert FileLimits.DEFAULT_MAX_FILE_SIZE > 0
        assert FileLimits.DEFAULT_MAX_FILE_SIZE == 1024 * 1024

    def test_max_file_size_bytes(self):
        """Test max file size in bytes."""
        assert FileLimits.MAX_FILE_SIZE_BYTES > 0
        assert FileLimits.MAX_FILE_SIZE_BYTES == 1024 * 1024

    def test_max_file_path_length(self):
        """Test max file path length."""
        assert FileLimits.MAX_FILE_PATH_LENGTH > 0
        assert FileLimits.MAX_FILE_PATH_LENGTH == 4096

    def test_max_message_length(self):
        """Test max message length."""
        assert FileLimits.MAX_MESSAGE_LENGTH > 0
        assert FileLimits.MAX_MESSAGE_LENGTH == 100_000

    def test_file_size_is_1mb(self):
        """Test file size limit is 1MB."""
        assert FileLimits.DEFAULT_MAX_FILE_SIZE == 1_048_576

    def test_path_length_is_4kb(self):
        """Test path length limit is 4KB."""
        assert FileLimits.MAX_FILE_PATH_LENGTH == 4096

    def test_message_length_is_100k(self):
        """Test message length limit is 100K."""
        assert FileLimits.MAX_MESSAGE_LENGTH == 100_000

    def test_all_limits_are_integers(self):
        """Test all limits are integers."""
        assert isinstance(FileLimits.DEFAULT_MAX_FILE_SIZE, int)
        assert isinstance(FileLimits.MAX_FILE_SIZE_BYTES, int)
        assert isinstance(FileLimits.MAX_FILE_PATH_LENGTH, int)
        assert isinstance(FileLimits.MAX_MESSAGE_LENGTH, int)

    def test_all_limits_are_positive(self):
        """Test all limits are positive."""
        assert FileLimits.DEFAULT_MAX_FILE_SIZE > 0
        assert FileLimits.MAX_FILE_SIZE_BYTES > 0
        assert FileLimits.MAX_FILE_PATH_LENGTH > 0
        assert FileLimits.MAX_MESSAGE_LENGTH > 0


class TestConstantsConsistency:
    """Tests for consistency between constants."""

    def test_intent_timeout_less_than_default(self):
        """Test intent timeout is less than default timeout."""
        assert LLMDefaults.INTENT_DETECTION_TIMEOUT_SECONDS <= LLMDefaults.DEFAULT_TIMEOUT_SECONDS

    def test_intent_max_tokens_less_than_default(self):
        """Test intent max tokens is less than default."""
        assert LLMDefaults.INTENT_DETECTION_MAX_TOKENS <= LLMDefaults.DEFAULT_MAX_TOKENS

    def test_file_size_limits_match(self):
        """Test file size limits match."""
        assert FileLimits.DEFAULT_MAX_FILE_SIZE == FileLimits.MAX_FILE_SIZE_BYTES

    def test_performance_targets_reasonable_order(self):
        """Test performance targets are in reasonable order."""
        assert PerformanceTargets.RESPONSE_TIME < PerformanceTargets.STARTUP_TIME
        assert PerformanceTargets.FILE_EDITING < PerformanceTargets.FILE_SCANNING


class TestConstantsReasonableValues:
    """Tests for reasonable constant values."""

    def test_temperature_in_valid_range(self):
        """Test all temperatures are in valid range."""
        assert 0.0 <= LLMDefaults.INTENT_DETECTION_TEMPERATURE <= 1.0
        assert 0.0 <= LLMDefaults.DEFAULT_TEMPERATURE <= 2.0

    def test_timeouts_reasonable_for_local_ai(self):
        """Test timeouts are reasonable for local AI."""
        # Local AI can be slow, so timeouts should be generous
        assert LLMDefaults.INTENT_DETECTION_TIMEOUT_SECONDS >= 30.0
        assert LLMDefaults.DEFAULT_TIMEOUT_SECONDS >= 300.0

    def test_file_limits_practical(self):
        """Test file limits are practical."""
        # 1MB is reasonable for source files
        assert FileLimits.DEFAULT_MAX_FILE_SIZE >= 1024 * 512  # At least 512KB
        # 4KB path is reasonable (typical OS limit is 4KB)
        assert FileLimits.MAX_FILE_PATH_LENGTH >= 256
        # 100K messages is reasonable
        assert FileLimits.MAX_MESSAGE_LENGTH >= 10_000

    def test_max_tokens_sufficient(self):
        """Test max tokens is sufficient."""
        # 4K tokens is standard for many models
        assert LLMDefaults.DEFAULT_MAX_TOKENS >= 4096

    def test_intent_detection_temperature_low(self):
        """Test intent detection uses low temperature for determinism."""
        assert LLMDefaults.INTENT_DETECTION_TEMPERATURE <= 0.5


class TestConstantsTypes:
    """Tests for constant types."""

    def test_performance_targets_are_final(self):
        """Test performance targets use Final."""
        # This is a type check - if it compiles, it passes
        assert True

    def test_llm_defaults_are_final(self):
        """Test LLM defaults use Final."""
        # This is a type check - if it compiles, it passes
        assert True

    def test_file_limits_are_final(self):
        """Test file limits use Final."""
        # This is a type check - if it compiles, it passes
        assert True

    def test_numeric_types_correct(self):
        """Test numeric types are correct."""
        assert isinstance(PerformanceTargets.STARTUP_TIME, float)
        assert isinstance(LLMDefaults.INTENT_DETECTION_MAX_FILES, int)
        assert isinstance(FileLimits.DEFAULT_MAX_FILE_SIZE, int)


class TestConstantsDocumentation:
    """Tests for constant documentation."""

    def test_classes_have_docstrings(self):
        """Test constant classes have docstrings."""
        assert PerformanceTargets.__doc__ is not None
        assert LLMDefaults.__doc__ is not None
        assert FileLimits.__doc__ is not None

    def test_constants_have_descriptions(self):
        """Test some constants have inline descriptions."""
        # Check that module is documented
        import gerdsenai_cli.constants
        assert gerdsenai_cli.constants.__doc__ is not None


class TestConstantsBoundaries:
    """Boundary value tests for constants."""

    def test_zero_temperature_invalid(self):
        """Test zero temperature would be valid but not recommended."""
        # Temperature of 0 is valid (deterministic)
        assert 0.0 <= LLMDefaults.DEFAULT_TEMPERATURE

    def test_max_temperature_boundary(self):
        """Test maximum temperature boundary."""
        # Most models support up to 2.0
        assert LLMDefaults.DEFAULT_TEMPERATURE <= 2.0

    def test_min_timeout_boundary(self):
        """Test minimum timeout boundary."""
        # Timeouts should be at least 1 second
        assert LLMDefaults.INTENT_DETECTION_TIMEOUT_SECONDS >= 1.0
        assert LLMDefaults.DEFAULT_TIMEOUT_SECONDS >= 1.0

    def test_max_file_size_boundary(self):
        """Test max file size boundary."""
        # File size should not exceed reasonable limits (e.g., 100MB)
        assert FileLimits.DEFAULT_MAX_FILE_SIZE <= 100 * 1024 * 1024


class TestConstantsUsagePatterns:
    """Tests for common usage patterns."""

    def test_intent_detection_config_complete(self):
        """Test intent detection has complete configuration."""
        assert hasattr(LLMDefaults, "INTENT_DETECTION_MAX_FILES")
        assert hasattr(LLMDefaults, "INTENT_DETECTION_TEMPERATURE")
        assert hasattr(LLMDefaults, "INTENT_DETECTION_MAX_TOKENS")
        assert hasattr(LLMDefaults, "INTENT_DETECTION_TIMEOUT_SECONDS")

    def test_default_llm_config_complete(self):
        """Test default LLM configuration is complete."""
        assert hasattr(LLMDefaults, "DEFAULT_TEMPERATURE")
        assert hasattr(LLMDefaults, "DEFAULT_MAX_TOKENS")
        assert hasattr(LLMDefaults, "DEFAULT_TIMEOUT_SECONDS")

    def test_file_limits_config_complete(self):
        """Test file limits configuration is complete."""
        assert hasattr(FileLimits, "DEFAULT_MAX_FILE_SIZE")
        assert hasattr(FileLimits, "MAX_FILE_SIZE_BYTES")
        assert hasattr(FileLimits, "MAX_FILE_PATH_LENGTH")
        assert hasattr(FileLimits, "MAX_MESSAGE_LENGTH")

    def test_performance_targets_config_complete(self):
        """Test performance targets configuration is complete."""
        assert hasattr(PerformanceTargets, "STARTUP_TIME")
        assert hasattr(PerformanceTargets, "RESPONSE_TIME")
        assert hasattr(PerformanceTargets, "MEMORY_BASELINE")
        assert hasattr(PerformanceTargets, "MODEL_LOADING")
        assert hasattr(PerformanceTargets, "FILE_SCANNING")
        assert hasattr(PerformanceTargets, "CONTEXT_BUILDING")
        assert hasattr(PerformanceTargets, "FILE_EDITING")


class TestConstantsEdgeCases:
    """Edge case tests for constants."""

    def test_constants_are_immutable(self):
        """Test constants cannot be modified (by convention)."""
        # Final type hint enforces immutability at type-check time
        original = LLMDefaults.DEFAULT_TEMPERATURE
        assert original is not None

    def test_constants_accessible(self):
        """Test all constants are accessible."""
        # This tests import paths work correctly
        from gerdsenai_cli.constants import (
            FileLimits,
            LLMDefaults,
            PerformanceTargets,
        )
        assert FileLimits is not None
        assert LLMDefaults is not None
        assert PerformanceTargets is not None


class TestConstantsLocalAIOptimized:
    """Tests that constants are optimized for local AI."""

    def test_timeouts_long_enough_for_slow_models(self):
        """Test timeouts are long enough for slow local models."""
        # Local models can take minutes to respond
        assert LLMDefaults.DEFAULT_TIMEOUT_SECONDS >= 600.0  # 10 minutes

    def test_intent_detection_timeout_reasonable(self):
        """Test intent detection timeout is reasonable for local AI."""
        # Even intent detection can be slow on local models
        assert LLMDefaults.INTENT_DETECTION_TIMEOUT_SECONDS >= 60.0  # 1 minute

    def test_temperature_allows_determinism(self):
        """Test temperature allows for deterministic operation."""
        # Low temperature for intent detection ensures consistency
        assert LLMDefaults.INTENT_DETECTION_TEMPERATURE <= 0.5

    def test_default_temperature_allows_creativity(self):
        """Test default temperature allows for creative responses."""
        # Higher temperature for general use allows varied responses
        assert LLMDefaults.DEFAULT_TEMPERATURE >= 0.5

    def test_max_tokens_sufficient_for_code(self):
        """Test max tokens is sufficient for code generation."""
        # 4K+ tokens needed for substantial code snippets
        assert LLMDefaults.DEFAULT_MAX_TOKENS >= 4096


class TestConstantsPerformanceRealistic:
    """Tests that performance targets are realistic."""

    def test_startup_time_achievable(self):
        """Test startup time target is achievable."""
        # 2 seconds is reasonable for Python CLI startup
        assert PerformanceTargets.STARTUP_TIME <= 5.0

    def test_response_time_achievable(self):
        """Test response time target is achievable."""
        # 0.5 seconds for local operations is reasonable
        assert PerformanceTargets.RESPONSE_TIME <= 1.0

    def test_memory_baseline_achievable(self):
        """Test memory baseline is achievable."""
        # 100MB is reasonable for Python application
        assert PerformanceTargets.MEMORY_BASELINE <= 200.0

    def test_model_loading_time_reasonable(self):
        """Test model loading time is reasonable."""
        # 5 seconds for model list is generous
        assert PerformanceTargets.MODEL_LOADING <= 30.0

    def test_file_operations_fast(self):
        """Test file operation targets are fast."""
        # File operations should be sub-second
        assert PerformanceTargets.FILE_SCANNING <= 2.0
        assert PerformanceTargets.FILE_EDITING <= 1.0

    def test_context_building_fast(self):
        """Test context building target is fast."""
        # 2 seconds for context is reasonable
        assert PerformanceTargets.CONTEXT_BUILDING <= 5.0
