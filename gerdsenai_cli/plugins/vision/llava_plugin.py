"""
LLaVA Vision Plugin for GerdsenAI CLI.

Integrates LLaVA (Large Language and Vision Assistant) via Ollama
for local image understanding capabilities.

LLaVA is a multimodal model that combines vision and language understanding,
capable of answering questions about images, describing visual content,
and performing OCR-like tasks.

Requirements:
- Ollama running locally
- LLaVA model installed: `ollama pull llava`

Supported LLaVA models:
- llava:7b - Smaller, faster (recommended for most uses)
- llava:13b - Larger, more accurate
- llava:34b - Highest quality (requires significant VRAM)
- bakllava - BakLLaVA variant with improved performance
"""

import base64
import logging
from pathlib import Path
from typing import Any

import httpx

from ..base import PluginCategory, PluginMetadata, VisionPlugin

logger = logging.getLogger(__name__)


class LLaVAPlugin:
    """
    LLaVA vision plugin via Ollama.

    Provides local image understanding capabilities using LLaVA models
    running in Ollama.
    """

    def __init__(
        self,
        ollama_url: str = "http://localhost:11434",
        default_model: str = "llava:7b",
        timeout: float = 60.0,
    ):
        """
        Initialize LLaVA plugin.

        Args:
            ollama_url: Ollama API base URL
            default_model: Default LLaVA model to use
            timeout: Request timeout in seconds
        """
        self.ollama_url = ollama_url
        self.default_model = default_model
        self.timeout = timeout

        self.metadata = PluginMetadata(
            name="llava",
            version="1.0.0",
            category=PluginCategory.VISION,
            description="LLaVA vision model integration via Ollama",
            author="GerdsenAI Team",
            dependencies=["ollama", "httpx"],
            capabilities=[
                "image_understanding",
                "visual_qa",
                "scene_description",
                "object_detection",
                "ocr_basic",
            ],
            configuration={
                "enabled": True,
                "ollama_url": ollama_url,
                "default_model": default_model,
                "timeout": timeout,
                "available_models": [
                    "llava:7b",
                    "llava:13b",
                    "llava:34b",
                    "bakllava",
                ],
            },
        )
        self._initialized = False
        self._available_models: list[str] = []

    async def initialize(self) -> bool:
        """
        Initialize LLaVA plugin.

        Checks if Ollama is running and if LLaVA models are available.

        Returns:
            True if initialization successful
        """
        logger.info("Initializing LLaVA vision plugin...")

        try:
            # Check if Ollama is running
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.ollama_url}/api/tags")
                response.raise_for_status()

                # Check for available LLaVA models
                data = response.json()
                self._available_models = [
                    model["name"]
                    for model in data.get("models", [])
                    if "llava" in model["name"].lower()
                    or "bakllava" in model["name"].lower()
                ]

                if not self._available_models:
                    logger.warning(
                        "No LLaVA models found in Ollama. "
                        "Install with: ollama pull llava"
                    )
                    return False

                logger.info(f"Found LLaVA models: {', '.join(self._available_models)}")

                # Verify default model exists
                if self.default_model not in self._available_models:
                    logger.warning(
                        f"Default model {self.default_model} not found. "
                        f"Using {self._available_models[0]} instead."
                    )
                    self.default_model = self._available_models[0]

                self._initialized = True
                logger.info("LLaVA plugin initialized successfully")
                return True

        except httpx.HTTPError as e:
            logger.error(f"Failed to connect to Ollama: {e}")
            logger.error("Ensure Ollama is running: https://ollama.ai")
            return False
        except Exception as e:
            logger.error(f"Failed to initialize LLaVA plugin: {e}")
            return False

    async def shutdown(self) -> None:
        """
        Cleanup LLaVA plugin resources.

        LLaVA models run in Ollama, so no local cleanup needed.
        """
        logger.info("Shutting down LLaVA plugin...")
        self._initialized = False
        self._available_models = []
        logger.info("LLaVA plugin shut down")

    async def health_check(self) -> dict[str, Any]:
        """
        Check LLaVA plugin health.

        Returns:
            Health status dictionary
        """
        if not self._initialized:
            return {
                "status": "unhealthy",
                "message": "Plugin not initialized",
                "details": {},
            }

        # Check if Ollama is still responding
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.ollama_url}/api/tags")
                response.raise_for_status()

                return {
                    "status": "healthy",
                    "message": "LLaVA plugin operational",
                    "details": {
                        "ollama_url": self.ollama_url,
                        "default_model": self.default_model,
                        "available_models": self._available_models,
                        "capabilities": self.metadata.capabilities,
                    },
                }

        except Exception as e:
            return {
                "status": "unhealthy",
                "message": f"Ollama connection failed: {e}",
                "details": {
                    "ollama_url": self.ollama_url,
                },
            }

    async def understand_image(
        self,
        image: str | Path | bytes,
        prompt: str | None = None,
        model: str | None = None,
        temperature: float = 0.7,
    ) -> str:
        """
        Understand image content using LLaVA.

        Args:
            image: Image file path, URL, or raw bytes
            prompt: Optional question about the image
            model: Optional specific model to use (defaults to default_model)
            temperature: Sampling temperature (0.0-1.0)

        Returns:
            LLaVA's description or answer about the image

        Raises:
            RuntimeError: If plugin not initialized
            ValueError: If image format is invalid
            httpx.HTTPError: If Ollama request fails
        """
        if not self._initialized:
            raise RuntimeError("LLaVA plugin not initialized")

        # Use default model if not specified
        model = model or self.default_model

        # Encode image to base64
        image_b64 = self._encode_image(image)

        # Default prompt if none provided
        if not prompt:
            prompt = "Describe this image in detail."

        # Prepare Ollama API request
        messages = [
            {
                "role": "user",
                "content": prompt,
                "images": [image_b64],
            }
        ]

        logger.info(f"Sending image to LLaVA model: {model}")
        logger.debug(f"Prompt: {prompt}")

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.ollama_url}/api/chat",
                    json={
                        "model": model,
                        "messages": messages,
                        "stream": False,
                        "options": {
                            "temperature": temperature,
                        },
                    },
                )
                response.raise_for_status()

                data = response.json()
                content = data.get("message", {}).get("content", "")

                if not content:
                    logger.warning("LLaVA returned empty response")
                    return "No response from LLaVA model."

                logger.info("LLaVA analysis complete")
                return content

        except httpx.TimeoutException:
            logger.error(f"LLaVA request timed out after {self.timeout}s")
            raise RuntimeError(
                f"LLaVA request timed out. Try:\n"
                f"- Using a smaller model (llava:7b)\n"
                f"- Increasing timeout\n"
                f"- Reducing image size"
            )
        except httpx.HTTPError as e:
            logger.error(f"LLaVA request failed: {e}")
            raise

    async def ocr(
        self,
        image: str | Path | bytes,
        languages: list[str] = ["en"],
        model: str | None = None,
    ) -> str:
        """
        Extract text from image using LLaVA.

        Note: LLaVA can perform basic OCR, but for production use cases,
        consider using dedicated OCR tools like TrOCR or PaddleOCR.

        Args:
            image: Image file path, URL, or raw bytes
            languages: Language codes (not used by LLaVA, for API compatibility)
            model: Optional specific model to use

        Returns:
            Extracted text
        """
        if not self._initialized:
            raise RuntimeError("LLaVA plugin not initialized")

        # Use LLaVA's vision understanding for OCR
        prompt = (
            "Extract all text from this image. "
            "Return only the text content, maintaining the original formatting. "
            "If there is no text, respond with 'No text found'."
        )

        return await self.understand_image(
            image=image,
            prompt=prompt,
            model=model,
            temperature=0.2,  # Lower temperature for more accurate text extraction
        )

    def _encode_image(self, image: str | Path | bytes) -> str:
        """
        Encode image to base64 string.

        Args:
            image: Image as file path, Path object, or raw bytes

        Returns:
            Base64 encoded image string

        Raises:
            ValueError: If image format is invalid
            FileNotFoundError: If image file doesn't exist
        """
        try:
            if isinstance(image, bytes):
                # Already bytes, encode directly
                return base64.b64encode(image).decode("utf-8")

            elif isinstance(image, (str, Path)):
                # File path - read and encode
                path = Path(image)

                if not path.exists():
                    raise FileNotFoundError(f"Image file not found: {path}")

                if not path.is_file():
                    raise ValueError(f"Path is not a file: {path}")

                with open(path, "rb") as f:
                    image_bytes = f.read()
                    return base64.b64encode(image_bytes).decode("utf-8")

            else:
                raise ValueError(f"Invalid image type: {type(image)}")

        except Exception as e:
            logger.error(f"Failed to encode image: {e}")
            raise

    def get_available_models(self) -> list[str]:
        """
        Get list of available LLaVA models.

        Returns:
            List of model names
        """
        return self._available_models.copy()

    async def pull_model(self, model_name: str) -> bool:
        """
        Pull/download a LLaVA model via Ollama.

        Args:
            model_name: Model to pull (e.g., "llava:7b")

        Returns:
            True if successful
        """
        logger.info(f"Pulling LLaVA model: {model_name}")

        try:
            async with httpx.AsyncClient(timeout=None) as client:
                # Start pull request
                async with client.stream(
                    "POST", f"{self.ollama_url}/api/pull", json={"name": model_name}
                ) as response:
                    response.raise_for_status()

                    # Stream progress updates
                    async for line in response.aiter_lines():
                        if line:
                            try:
                                import json

                                data = json.loads(line)
                                status = data.get("status", "")
                                logger.info(f"Pull status: {status}")
                            except json.JSONDecodeError:
                                continue

            logger.info(f"Successfully pulled model: {model_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to pull model {model_name}: {e}")
            return False


# Export plugin class for auto-discovery
__all__ = ["LLaVAPlugin"]
