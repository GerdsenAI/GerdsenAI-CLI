"""
LLM Provider Abstraction Layer.

This module provides a unified interface for interacting with various
local LLM providers (Ollama, vLLM, LM Studio, Hugging Face, etc.).
"""

from .base import LLMProvider, ModelInfo, ProviderCapabilities, ProviderType
from .detector import ProviderDetector
from .huggingface import HuggingFaceProvider
from .lm_studio import LMStudioProvider
from .ollama import OllamaProvider
from .vllm import VLLMProvider

__all__ = [
    "LLMProvider",
    "ModelInfo",
    "ProviderCapabilities",
    "ProviderType",
    "ProviderDetector",
    "OllamaProvider",
    "VLLMProvider",
    "LMStudioProvider",
    "HuggingFaceProvider",
]
