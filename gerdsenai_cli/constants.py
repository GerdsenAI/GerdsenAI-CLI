"""
Central Constants Module for GerdsenAI CLI.

This module consolidates magic numbers, hardcoded values, and configuration
constants that are used across the codebase. Centralizing these values:
- Improves maintainability
- Prevents duplication
- Makes configuration easier
- Enables runtime customization

Categories:
- Performance thresholds
- LLM inference parameters
- File handling limits
- Provider defaults
- UI/UX constants
"""

from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    pass

# =============================================================================
# PERFORMANCE THRESHOLDS
# =============================================================================


class PerformanceTargets:
    """Performance targets for various operations (in seconds)."""

    STARTUP_TIME: Final[float] = 2.0
    """< 2 seconds to interactive prompt"""

    RESPONSE_TIME: Final[float] = 0.5
    """< 500ms for local operations"""

    MEMORY_BASELINE: Final[float] = 100.0
    """< 100MB baseline memory footprint"""

    MODEL_LOADING: Final[float] = 5.0
    """< 5 seconds to load model list"""

    FILE_SCANNING: Final[float] = 1.0
    """< 1 second for typical project directories"""

    CONTEXT_BUILDING: Final[float] = 2.0
    """< 2 seconds for project analysis"""

    FILE_EDITING: Final[float] = 0.5
    """< 500ms for diff generation and validation"""


# =============================================================================
# LLM INFERENCE PARAMETERS
# =============================================================================


class LLMDefaults:
    """Default parameters for LLM inference operations."""

    # Intent detection parameters
    INTENT_DETECTION_MAX_FILES: Final[int] = 100
    """Maximum number of files to include in intent detection context"""

    INTENT_DETECTION_TEMPERATURE: Final[float] = 0.3
    """Low temperature for deterministic intent detection"""

    INTENT_DETECTION_MAX_TOKENS: Final[int] = 300
    """Maximum tokens for intent detection responses"""

    INTENT_DETECTION_TIMEOUT_SECONDS: Final[float] = 60.0
    """Timeout for intent detection requests (increased for local AI)"""

    # General completion parameters
    DEFAULT_TEMPERATURE: Final[float] = 0.7
    """Default temperature for general completions"""

    DEFAULT_MAX_TOKENS: Final[int] = 4096
    """Default maximum tokens for responses (increased for better responses)"""

    DEFAULT_TIMEOUT_SECONDS: Final[float] = 600.0
    """Default timeout for LLM requests (10 minutes for local AI)"""


# =============================================================================
# FILE HANDLING LIMITS
# =============================================================================


class FileLimits:
    """Limits for file operations and context management."""

    DEFAULT_MAX_FILE_SIZE: Final[int] = 1024 * 1024
    """Default maximum file size to read (1MB)"""

    MAX_FILE_SIZE_BYTES: Final[int] = 1024 * 1024
    """Maximum file size in bytes for clarity"""

    MAX_FILE_PATH_LENGTH: Final[int] = 4096
    """Maximum length for file paths"""

    MAX_MESSAGE_LENGTH: Final[int] = 100_000
    """Maximum length for user messages (100KB)"""

    MAX_CONTEXT_FILES: Final[int] = 100
    """Maximum number of files to include in context"""


# =============================================================================
# PROVIDER DEFAULTS
# =============================================================================

# Note: ProviderType is defined in gerdsenai_cli.core.providers.base
# To avoid circular imports, we use string keys here


class ProviderDefaults:
    """Default configuration for LLM providers.

    Single source of truth for provider default configurations.
    Use string keys to avoid circular imports with providers.base module.
    """

    CONFIGURATIONS = {
        "ollama": {
            "protocol": "http",
            "host": "localhost",
            "port": 11434,
            "description": "Ollama (default configuration)",
            "health_endpoint": "/api/tags",
        },
        "lm_studio": {
            "protocol": "http",
            "host": "localhost",
            "port": 1234,
            "description": "LM Studio (default configuration)",
            "health_endpoint": "/v1/models",
        },
        "vllm": {
            "protocol": "http",
            "host": "localhost",
            "port": 8000,
            "description": "vLLM (default configuration)",
            "health_endpoint": "/v1/models",
        },
        "huggingface_tgi": {
            "protocol": "http",
            "host": "localhost",
            "port": 8080,
            "description": "HuggingFace TGI (default configuration)",
            "health_endpoint": "/health",
        },
    }

    @classmethod
    def get_url(cls, provider_key: str) -> str:
        """Get the default URL for a provider."""
        cfg = cls.CONFIGURATIONS.get(provider_key)
        if not cfg:
            raise ValueError(f"Unknown provider: {provider_key}")
        return f"{cfg['protocol']}://{cfg['host']}:{cfg['port']}"

    @classmethod
    def get_config(cls, provider_key: str) -> dict:
        """Get configuration for a provider."""
        cfg = cls.CONFIGURATIONS.get(provider_key)
        if not cfg:
            raise ValueError(f"Unknown provider: {provider_key}")
        return cfg.copy()

    @classmethod
    def get_common_configs(cls) -> list[tuple[str, str]]:
        """Get list of (URL, description) tuples for common configurations."""
        return [
            (cls.get_url(pkey), cfg["description"])
            for pkey, cfg in cls.CONFIGURATIONS.items()
        ]


# =============================================================================
# FILE TYPE MAPPINGS
# =============================================================================


class FileTypeMapping:
    """Centralized file extension to language/type mappings."""

    MAPPINGS = {
        # Python
        ".py": {"language": "python", "display": "Python", "category": "code"},
        ".pyi": {"language": "python", "display": "Python Stub", "category": "code"},
        ".pyx": {"language": "cython", "display": "Cython", "category": "code"},
        # JavaScript/TypeScript
        ".js": {"language": "javascript", "display": "JavaScript", "category": "code"},
        ".mjs": {
            "language": "javascript",
            "display": "JavaScript Module",
            "category": "code",
        },
        ".jsx": {
            "language": "javascriptreact",
            "display": "JavaScript React",
            "category": "code",
        },
        ".ts": {"language": "typescript", "display": "TypeScript", "category": "code"},
        ".tsx": {
            "language": "typescriptreact",
            "display": "TypeScript React",
            "category": "code",
        },
        # Web
        ".html": {"language": "html", "display": "HTML", "category": "code"},
        ".htm": {"language": "html", "display": "HTML", "category": "code"},
        ".css": {"language": "css", "display": "CSS", "category": "code"},
        ".scss": {"language": "scss", "display": "SCSS", "category": "code"},
        ".sass": {"language": "sass", "display": "Sass", "category": "code"},
        ".less": {"language": "less", "display": "Less", "category": "code"},
        # Configuration
        ".json": {"language": "json", "display": "JSON", "category": "config"},
        ".yaml": {"language": "yaml", "display": "YAML", "category": "config"},
        ".yml": {"language": "yaml", "display": "YAML", "category": "config"},
        ".toml": {"language": "toml", "display": "TOML", "category": "config"},
        ".xml": {"language": "xml", "display": "XML", "category": "config"},
        ".ini": {"language": "ini", "display": "INI", "category": "config"},
        # Markdown/Documentation
        ".md": {"language": "markdown", "display": "Markdown", "category": "docs"},
        ".markdown": {
            "language": "markdown",
            "display": "Markdown",
            "category": "docs",
        },
        ".rst": {
            "language": "restructuredtext",
            "display": "reStructuredText",
            "category": "docs",
        },
        ".txt": {"language": "plaintext", "display": "Plain Text", "category": "docs"},
        # Systems languages
        ".c": {"language": "c", "display": "C", "category": "code"},
        ".h": {"language": "c", "display": "C Header", "category": "code"},
        ".cpp": {"language": "cpp", "display": "C++", "category": "code"},
        ".hpp": {"language": "cpp", "display": "C++ Header", "category": "code"},
        ".rs": {"language": "rust", "display": "Rust", "category": "code"},
        ".go": {"language": "go", "display": "Go", "category": "code"},
        # JVM languages
        ".java": {"language": "java", "display": "Java", "category": "code"},
        ".kt": {"language": "kotlin", "display": "Kotlin", "category": "code"},
        ".scala": {"language": "scala", "display": "Scala", "category": "code"},
        # Other
        ".sh": {"language": "bash", "display": "Shell Script", "category": "code"},
        ".bash": {"language": "bash", "display": "Bash Script", "category": "code"},
        ".zsh": {"language": "zsh", "display": "Zsh Script", "category": "code"},
        ".sql": {"language": "sql", "display": "SQL", "category": "code"},
        ".rb": {"language": "ruby", "display": "Ruby", "category": "code"},
        ".php": {"language": "php", "display": "PHP", "category": "code"},
        ".swift": {"language": "swift", "display": "Swift", "category": "code"},
    }

    @classmethod
    def get_language(cls, extension: str) -> str:
        """Get language identifier for syntax highlighting."""
        return cls.MAPPINGS.get(extension, {}).get("language", "plaintext")

    @classmethod
    def get_display_name(cls, extension: str) -> str:
        """Get human-readable display name."""
        return cls.MAPPINGS.get(extension, {}).get("display", extension)

    @classmethod
    def get_category(cls, extension: str) -> str:
        """Get file category (code/config/docs)."""
        return cls.MAPPINGS.get(extension, {}).get("category", "unknown")


# =============================================================================
# TEXT FILE EXTENSIONS
# =============================================================================

TEXT_FILE_EXTENSIONS: Final[frozenset[str]] = frozenset(
    [
        # Code
        ".py",
        ".pyi",
        ".pyx",
        ".js",
        ".mjs",
        ".jsx",
        ".ts",
        ".tsx",
        ".c",
        ".h",
        ".cpp",
        ".hpp",
        ".cc",
        ".cxx",
        ".rs",
        ".go",
        ".java",
        ".kt",
        ".scala",
        ".rb",
        ".php",
        ".swift",
        ".lua",
        ".sh",
        ".bash",
        ".zsh",
        ".fish",
        # Web
        ".html",
        ".htm",
        ".css",
        ".scss",
        ".sass",
        ".less",
        ".svg",
        ".vue",
        ".svelte",
        # Configuration
        ".json",
        ".yaml",
        ".yml",
        ".toml",
        ".xml",
        ".ini",
        ".conf",
        ".config",
        ".env",
        # Documentation
        ".md",
        ".markdown",
        ".rst",
        ".txt",
        ".tex",
        ".adoc",
        ".asciidoc",
        # Data
        ".sql",
        ".graphql",
        ".proto",
        ".csv",
        ".tsv",
    ]
)


# =============================================================================
# DEFAULT IGNORE PATTERNS
# =============================================================================

DEFAULT_IGNORE_PATTERNS: Final[frozenset[str]] = frozenset(
    [
        # Version control
        ".git",
        ".svn",
        ".hg",
        ".bzr",
        # Dependencies
        "node_modules",
        "venv",
        "env",
        ".env",
        ".venv",
        "virtualenv",
        "__pycache__",
        "site-packages",
        "dist-packages",
        "vendor",
        "bower_components",
        # Build outputs
        "dist",
        "build",
        "out",
        "target",
        ".next",
        ".nuxt",
        ".output",
        "coverage",
        ".coverage",
        # IDE/Editor
        ".vscode",
        ".idea",
        ".vs",
        "*.swp",
        "*.swo",
        "*~",
        ".DS_Store",
        "Thumbs.db",
        # Package managers
        ".npm",
        ".yarn",
        ".pnpm-store",
        "Cargo.lock",
        "package-lock.json",
        "yarn.lock",
        "pnpm-lock.yaml",
        # Temporary
        "tmp",
        "temp",
        ".tmp",
        ".cache",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        ".tox",
    ]
)


# =============================================================================
# UI/UX CONSTANTS
# =============================================================================


class UIConstants:
    """Constants for UI/UX behavior."""

    # TUI streaming
    STREAMING_CHUNK_DELAY: Final[float] = 0.01
    """Delay between chunks for smooth typewriter effect (seconds)"""

    STREAMING_REFRESH_INTERVAL: Final[int] = 10
    """Refresh display every N chunks"""

    # Input validation
    MIN_INPUT_INTERVAL_MS: Final[int] = 100
    """Minimum time between inputs to prevent spam (milliseconds)"""

    # Display limits
    MAX_ERROR_DISPLAY_LENGTH: Final[int] = 1000
    """Maximum length for error messages in UI"""

    MAX_LOG_LINE_LENGTH: Final[int] = 500
    """Maximum length for log lines in display"""

    CONTEXT_FILE_DISPLAY_THRESHOLD: Final[int] = 0
    """Minimum number of context files to show notification"""


# =============================================================================
# ERROR MESSAGE FORMATTING
# =============================================================================


class ErrorMessageStyle:
    """Standard formatting for error messages."""

    # Emoji prefixes for consistency
    ERROR_PREFIX: Final[str] = "❌"
    WARNING_PREFIX: Final[str] = "⚠️ "
    INFO_PREFIX: Final[str] = "ℹ️ "
    SUCCESS_PREFIX: Final[str] = "✅"

    # Common error patterns
    @staticmethod
    def format_error(message: str, include_emoji: bool = True) -> str:
        """Format error message with standard prefix."""
        prefix = f"{ErrorMessageStyle.ERROR_PREFIX} " if include_emoji else ""
        return f"{prefix}{message}"

    @staticmethod
    def format_warning(message: str, include_emoji: bool = True) -> str:
        """Format warning message with standard prefix."""
        prefix = ErrorMessageStyle.WARNING_PREFIX if include_emoji else ""
        return f"{prefix}{message}"

    @staticmethod
    def format_info(message: str, include_emoji: bool = True) -> str:
        """Format info message with standard prefix."""
        prefix = ErrorMessageStyle.INFO_PREFIX if include_emoji else ""
        return f"{prefix}{message}"

    @staticmethod
    def format_success(message: str, include_emoji: bool = True) -> str:
        """Format success message with standard prefix."""
        prefix = f"{ErrorMessageStyle.SUCCESS_PREFIX} " if include_emoji else ""
        return f"{prefix}{message}"


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    "PerformanceTargets",
    "LLMDefaults",
    "FileLimits",
    "ProviderDefaults",
    "FileTypeMapping",
    "TEXT_FILE_EXTENSIONS",
    "DEFAULT_IGNORE_PATTERNS",
    "UIConstants",
    "ErrorMessageStyle",
]
