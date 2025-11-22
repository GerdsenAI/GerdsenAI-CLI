"""
Accurate token counting using tiktoken.

This module provides precise token counting for various LLM models,
replacing the simple heuristic (~4 chars per token) with actual tokenization.
"""

import logging
from functools import lru_cache
from typing import Any

logger = logging.getLogger(__name__)

# Try to import tiktoken
try:
    import tiktoken

    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False
    logger.warning("tiktoken not available, falling back to heuristic token counting")


# Model family to encoding mapping
MODEL_ENCODINGS = {
    # OpenAI models
    "gpt-4": "cl100k_base",
    "gpt-3.5": "cl100k_base",
    "text-embedding-ada": "cl100k_base",
    # Common local models
    "llama": "cl100k_base",  # Approximate
    "mistral": "cl100k_base",  # Approximate
    "mixtral": "cl100k_base",  # Approximate
    "qwen": "cl100k_base",  # Approximate
    "deepseek": "cl100k_base",  # Approximate
    "codellama": "cl100k_base",  # Approximate
    "phi": "cl100k_base",  # Approximate
    "gemma": "cl100k_base",  # Approximate
    "yi": "cl100k_base",  # Approximate
    # Fallback
    "default": "cl100k_base",
}


@lru_cache(maxsize=128)
def get_encoding(model_name: str) -> Any:
    """
    Get tiktoken encoding for a model.

    Args:
        model_name: Model name (e.g., "llama-2-7b", "gpt-4")

    Returns:
        tiktoken encoding object

    Raises:
        RuntimeError: If tiktoken is not available
    """
    if not TIKTOKEN_AVAILABLE:
        raise RuntimeError("tiktoken is not installed")

    # Determine encoding based on model name
    encoding_name = MODEL_ENCODINGS["default"]

    for model_family, enc in MODEL_ENCODINGS.items():
        if model_family.lower() in model_name.lower():
            encoding_name = enc
            break

    try:
        return tiktoken.get_encoding(encoding_name)
    except Exception as e:
        logger.warning(f"Failed to get encoding {encoding_name}: {e}, using default")
        return tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str, model: str = "default") -> int:
    """
    Count tokens in text using tiktoken.

    Args:
        text: Text to count tokens for
        model: Model name (for encoding selection)

    Returns:
        Number of tokens
    """
    if not text:
        return 0

    if TIKTOKEN_AVAILABLE:
        try:
            encoding = get_encoding(model)
            tokens = encoding.encode(text, disallowed_special=())
            return len(tokens)
        except Exception as e:
            logger.warning(f"tiktoken failed, falling back to heuristic: {e}")
            # Fallback to heuristic
            return estimate_tokens_heuristic(text)
    else:
        # Fallback to heuristic
        return estimate_tokens_heuristic(text)


def estimate_tokens_heuristic(text: str) -> int:
    """
    Estimate token count using simple heuristic.

    This is a fallback when tiktoken is not available.
    Approximate: ~4 characters per token for English text.

    Args:
        text: Text to estimate tokens for

    Returns:
        Estimated number of tokens
    """
    if not text:
        return 0
    return len(text) // 4


def count_messages_tokens(
    messages: list[dict[str, str]], model: str = "default"
) -> int:
    """
    Count total tokens in a list of chat messages.

    Args:
        messages: List of message dictionaries with 'role' and 'content'
        model: Model name

    Returns:
        Total token count (includes message formatting overhead)
    """
    total_tokens = 0

    for message in messages:
        # Count tokens in content
        content = message.get("content", "")
        total_tokens += count_tokens(content, model)

        # Add formatting overhead per message
        # Most chat models add ~4 tokens per message for formatting
        total_tokens += 4

        # Add tokens for role
        role = message.get("role", "")
        total_tokens += count_tokens(role, model)

    # Add conversation-level overhead (~3 tokens)
    total_tokens += 3

    return total_tokens


def estimate_max_response_tokens(
    messages: list[dict[str, str]],
    model: str = "default",
    context_window: int = 4096,
    context_usage: float = 0.8,
) -> int:
    """
    Estimate maximum response tokens available.

    The context_usage parameter controls the input/response allocation:
    - Higher values (e.g., 0.9) allocate more to input, less to response
    - Lower values (e.g., 0.5) allocate more to response, less to input

    Args:
        messages: Chat messages
        model: Model name
        context_window: Model's context window size
        context_usage: Fraction of context to allocate to input (default 0.8)
                      Response gets (1.0 - context_usage) of the context

    Returns:
        Maximum tokens available for response
    """
    # Count tokens in messages
    input_tokens = count_messages_tokens(messages, model)

    # Calculate response budget: higher context_usage means less for response
    # context_usage=0.8 -> response gets 20% of window = 819 tokens
    # context_usage=0.5 -> response gets 50% of window = 2048 tokens
    response_budget = int(context_window * (1.0 - context_usage))

    # Also calculate how much space is actually remaining
    remaining_space = context_window - input_tokens

    # Return the smaller of: allocated budget or actual remaining space
    return max(0, min(response_budget, remaining_space))


def truncate_messages_to_fit(
    messages: list[dict[str, str]],
    model: str = "default",
    context_window: int = 4096,
    context_usage: float = 0.8,
) -> list[dict[str, str]]:
    """
    Truncate messages to fit within context window.

    Keeps the most recent messages, ensuring system message is preserved.

    Args:
        messages: Chat messages
        model: Model name
        context_window: Model's context window size
        context_usage: Fraction of context to use for input

    Returns:
        Truncated messages list
    """
    if not messages:
        return []

    # Calculate max tokens for input
    max_input_tokens = int(context_window * context_usage)

    # Separate system message (first message if role is 'system')
    system_message = None
    conversation_messages = messages

    if messages and messages[0].get("role") == "system":
        system_message = messages[0]
        conversation_messages = messages[1:]

    # Start with most recent messages and work backwards
    truncated = []
    current_tokens = 0

    # Add system message tokens if present
    if system_message:
        system_tokens = count_messages_tokens([system_message], model)
        current_tokens += system_tokens

    # Add messages from most recent backwards
    for message in reversed(conversation_messages):
        message_tokens = count_messages_tokens([message], model)

        if current_tokens + message_tokens <= max_input_tokens:
            truncated.insert(0, message)
            current_tokens += message_tokens
        else:
            break

    # Prepend system message if it was present
    if system_message:
        truncated.insert(0, system_message)

    logger.info(
        f"Truncated messages: {len(messages)} -> {len(truncated)} (tokens: ~{current_tokens})"
    )

    return truncated


class TokenCounter:
    """
    Token counter with caching for performance.

    Provides methods for counting tokens with automatic caching
    of results to avoid redundant tokenization.
    """

    def __init__(self, model: str = "default", cache_size: int = 256):
        """
        Initialize token counter.

        Args:
            model: Model name for encoding selection
            cache_size: LRU cache size for counted text
        """
        self.model = model
        self.cache_size = cache_size
        self._cache: dict[str, int] = {}

    def count(self, text: str) -> int:
        """
        Count tokens with caching.

        Args:
            text: Text to count

        Returns:
            Token count
        """
        if text in self._cache:
            return self._cache[text]

        count = count_tokens(text, self.model)

        # Maintain cache size
        if len(self._cache) >= self.cache_size:
            # Remove oldest entry (simple FIFO)
            self._cache.pop(next(iter(self._cache)))

        self._cache[text] = count
        return count

    def count_messages(self, messages: list[dict[str, str]]) -> int:
        """
        Count tokens in messages.

        Args:
            messages: Chat messages

        Returns:
            Total token count
        """
        return count_messages_tokens(messages, self.model)

    def clear_cache(self) -> None:
        """Clear the token count cache."""
        self._cache.clear()


# Global counter instance
_global_counter: TokenCounter | None = None


def get_token_counter(model: str = "default") -> TokenCounter:
    """
    Get or create global token counter.

    Args:
        model: Model name

    Returns:
        Global TokenCounter instance
    """
    global _global_counter
    if _global_counter is None or _global_counter.model != model:
        _global_counter = TokenCounter(model=model)
    return _global_counter
