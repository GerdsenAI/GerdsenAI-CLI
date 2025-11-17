"""
Whisper Speech-to-Text Plugin for GerdsenAI CLI.

Integrates OpenAI's Whisper model for local speech recognition
and transcription capabilities.

Whisper is a versatile speech recognition model that can transcribe
audio in 99 languages, translate to English, and perform language identification.

Requirements:
- faster-whisper (recommended) OR openai-whisper
- ffmpeg (for audio processing)

Installation:
- faster-whisper: pip install faster-whisper
- openai-whisper: pip install openai-whisper
- ffmpeg:
  - Ubuntu/Debian: sudo apt install ffmpeg
  - macOS: brew install ffmpeg
  - Windows: https://ffmpeg.org/download.html

Supported Models:
- tiny (39M params) - Fastest, lowest accuracy
- base (74M params) - Good balance for quick transcription
- small (244M params) - Better accuracy
- medium (769M params) - High accuracy
- large-v3 (1550M params) - Highest accuracy (recommended)
"""

import logging
import shutil
from pathlib import Path
from typing import Any

from ..base import PluginCategory, PluginMetadata

logger = logging.getLogger(__name__)


class WhisperPlugin:
    """
    Whisper speech-to-text plugin.

    Provides local speech recognition and transcription using
    OpenAI's Whisper models via faster-whisper or openai-whisper.
    """

    def __init__(
        self,
        model_size: str = "base",
        device: str = "auto",
        compute_type: str = "auto",
        use_faster_whisper: bool = True,
    ):
        """
        Initialize Whisper plugin.

        Args:
            model_size: Model size (tiny, base, small, medium, large-v3)
            device: Device to use (cpu, cuda, auto)
            compute_type: Compute type (int8, float16, float32, auto)
            use_faster_whisper: Use faster-whisper if available (recommended)
        """
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.use_faster_whisper = use_faster_whisper

        self.metadata = PluginMetadata(
            name="whisper",
            version="1.0.0",
            category=PluginCategory.AUDIO,
            description="Whisper speech-to-text transcription",
            author="GerdsenAI Team",
            dependencies=["faster-whisper", "ffmpeg"],
            capabilities=[
                "speech_to_text",
                "transcription",
                "translation",
                "language_detection",
                "timestamp_generation",
                "multi_language",
            ],
            configuration={
                "enabled": True,
                "model_size": model_size,
                "device": device,
                "compute_type": compute_type,
                "use_faster_whisper": use_faster_whisper,
                "available_models": [
                    "tiny",
                    "base",
                    "small",
                    "medium",
                    "large-v3",
                ],
            }
        )
        self._initialized = False
        self._model = None
        self._using_faster_whisper = False

    async def initialize(self) -> bool:
        """
        Initialize Whisper plugin.

        Checks for dependencies and loads the model.

        Returns:
            True if initialization successful
        """
        logger.info("Initializing Whisper speech-to-text plugin...")

        # Check for ffmpeg
        if not shutil.which("ffmpeg"):
            logger.error(
                "ffmpeg not found. Install with:\n"
                "  Ubuntu/Debian: sudo apt install ffmpeg\n"
                "  macOS: brew install ffmpeg\n"
                "  Windows: https://ffmpeg.org/download.html"
            )
            return False

        logger.info("Found ffmpeg")

        # Try faster-whisper first (recommended)
        if self.use_faster_whisper:
            try:
                import faster_whisper

                logger.info("Using faster-whisper (optimized)")

                # Determine device
                if self.device == "auto":
                    try:
                        import torch
                        device = "cuda" if torch.cuda.is_available() else "cpu"
                    except ImportError:
                        device = "cpu"
                else:
                    device = self.device

                # Determine compute type
                if self.compute_type == "auto":
                    compute_type = "int8" if device == "cpu" else "float16"
                else:
                    compute_type = self.compute_type

                logger.info(f"Loading Whisper {self.model_size} model...")
                logger.info(f"Device: {device}, Compute type: {compute_type}")

                self._model = faster_whisper.WhisperModel(
                    self.model_size,
                    device=device,
                    compute_type=compute_type,
                )

                self._using_faster_whisper = True
                self._initialized = True
                logger.info("Whisper plugin initialized successfully (faster-whisper)")
                return True

            except ImportError:
                logger.warning(
                    "faster-whisper not available, trying openai-whisper\n"
                    "Install for better performance: pip install faster-whisper"
                )
            except Exception as e:
                logger.warning(f"faster-whisper initialization failed: {e}")

        # Fallback to openai-whisper
        try:
            import whisper

            logger.info("Using openai-whisper (fallback)")

            logger.info(f"Loading Whisper {self.model_size} model...")
            self._model = whisper.load_model(self.model_size)

            self._using_faster_whisper = False
            self._initialized = True
            logger.info("Whisper plugin initialized successfully (openai-whisper)")
            return True

        except ImportError:
            logger.error(
                "Whisper not available. Install with:\n"
                "  Recommended: pip install faster-whisper\n"
                "  Alternative: pip install openai-whisper"
            )
            return False
        except Exception as e:
            logger.error(f"Failed to initialize Whisper plugin: {e}")
            return False

    async def shutdown(self) -> None:
        """
        Cleanup Whisper plugin resources.

        Unloads the model to free memory.
        """
        logger.info("Shutting down Whisper plugin...")
        self._initialized = False
        self._model = None
        self._using_faster_whisper = False
        logger.info("Whisper plugin shut down")

    async def health_check(self) -> dict[str, Any]:
        """
        Check Whisper plugin health.

        Returns:
            Health status dictionary
        """
        if not self._initialized:
            return {
                "status": "unhealthy",
                "message": "Plugin not initialized",
                "details": {}
            }

        # Check if ffmpeg still available
        if not shutil.which("ffmpeg"):
            return {
                "status": "unhealthy",
                "message": "ffmpeg not found",
                "details": {}
            }

        return {
            "status": "healthy",
            "message": "Whisper plugin operational",
            "details": {
                "model_size": self.model_size,
                "engine": "faster-whisper" if self._using_faster_whisper else "openai-whisper",
                "device": self.device,
                "capabilities": self.metadata.capabilities,
            }
        }

    async def transcribe(
        self,
        audio: str | Path,
        language: str | None = None,
        task: str = "transcribe",
        return_timestamps: bool = False,
        initial_prompt: str | None = None,
    ) -> dict[str, Any]:
        """
        Transcribe audio file to text.

        Args:
            audio: Path to audio file (mp3, wav, m4a, etc.)
            language: Language code (e.g., "en", "es", "fr") or None for auto-detect
            task: "transcribe" or "translate" (translate to English)
            return_timestamps: Include word-level timestamps
            initial_prompt: Optional prompt to guide transcription

        Returns:
            Dictionary with transcription results:
            - text: Full transcription
            - language: Detected/specified language
            - segments: List of segments with timestamps (if requested)
            - duration: Audio duration in seconds

        Raises:
            RuntimeError: If plugin not initialized
            FileNotFoundError: If audio file doesn't exist
            ValueError: If audio format invalid
        """
        if not self._initialized:
            raise RuntimeError("Whisper plugin not initialized")

        # Validate audio file
        audio_path = Path(audio)
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio}")
        if not audio_path.is_file():
            raise ValueError(f"Path is not a file: {audio}")

        logger.info(f"Transcribing audio: {audio_path.name}")
        if language:
            logger.info(f"Language: {language}")
        logger.info(f"Task: {task}")

        try:
            if self._using_faster_whisper:
                # faster-whisper implementation
                segments, info = self._model.transcribe(
                    str(audio_path),
                    language=language,
                    task=task,
                    word_timestamps=return_timestamps,
                    initial_prompt=initial_prompt,
                )

                # Collect segments
                segment_list = []
                full_text = []

                for segment in segments:
                    segment_dict = {
                        "start": segment.start,
                        "end": segment.end,
                        "text": segment.text,
                    }
                    if return_timestamps and hasattr(segment, "words"):
                        segment_dict["words"] = [
                            {
                                "start": word.start,
                                "end": word.end,
                                "word": word.word,
                                "probability": word.probability,
                            }
                            for word in segment.words
                        ]
                    segment_list.append(segment_dict)
                    full_text.append(segment.text)

                result = {
                    "text": " ".join(full_text).strip(),
                    "language": info.language,
                    "language_probability": info.language_probability,
                    "duration": info.duration,
                    "segments": segment_list if segment_list else None,
                }

            else:
                # openai-whisper implementation
                result_raw = self._model.transcribe(
                    str(audio_path),
                    language=language,
                    task=task,
                    word_timestamps=return_timestamps,
                    initial_prompt=initial_prompt,
                )

                result = {
                    "text": result_raw["text"].strip(),
                    "language": result_raw.get("language"),
                    "duration": None,  # Not available in openai-whisper
                    "segments": result_raw.get("segments") if return_timestamps else None,
                }

            logger.info(f"Transcription complete - Language: {result['language']}")
            logger.info(f"Transcribed {len(result['text'])} characters")

            return result

        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            raise

    async def detect_language(
        self,
        audio: str | Path,
    ) -> dict[str, Any]:
        """
        Detect the language of an audio file.

        Args:
            audio: Path to audio file

        Returns:
            Dictionary with language detection results:
            - language: ISO 639-1 language code
            - probability: Confidence score (0-1)

        Raises:
            RuntimeError: If plugin not initialized
        """
        if not self._initialized:
            raise RuntimeError("Whisper plugin not initialized")

        audio_path = Path(audio)
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio}")

        logger.info(f"Detecting language: {audio_path.name}")

        try:
            if self._using_faster_whisper:
                # faster-whisper has dedicated language detection
                segments, info = self._model.transcribe(
                    str(audio_path),
                    language=None,  # Auto-detect
                )

                # Consume first segment to trigger detection
                try:
                    next(segments)
                except StopIteration:
                    pass

                result = {
                    "language": info.language,
                    "probability": info.language_probability,
                }

            else:
                # openai-whisper: transcribe short segment for detection
                result_raw = self._model.transcribe(
                    str(audio_path),
                    language=None,
                )

                result = {
                    "language": result_raw.get("language", "unknown"),
                    "probability": None,  # Not available
                }

            logger.info(f"Detected language: {result['language']} (confidence: {result.get('probability', 'N/A')})")
            return result

        except Exception as e:
            logger.error(f"Language detection failed: {e}")
            raise

    def get_available_models(self) -> list[str]:
        """
        Get list of available Whisper models.

        Returns:
            List of model names
        """
        return self.metadata.configuration["available_models"]


# Export plugin class for auto-discovery
__all__ = ["WhisperPlugin"]
