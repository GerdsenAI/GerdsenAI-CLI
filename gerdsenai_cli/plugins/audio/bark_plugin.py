"""
Bark Text-to-Speech Plugin for GerdsenAI CLI.

Integrates Suno's Bark model for local text-to-speech generation
with realistic, natural-sounding voices.

Bark is a transformer-based TTS model that can generate speech with:
- Natural prosody and intonation
- Multiple voice presets (male, female, various accents)
- Non-verbal communication (laughter, sighs, etc.)
- Multi-language support

Requirements:
- bark (suno-bark package)
- scipy (for audio output)
- numpy

Installation:
- pip install git+https://github.com/suno-ai/bark.git
- pip install scipy numpy

Model Sizes:
- Small models: ~2GB download
- Full models: ~10GB download (higher quality)

Voice Presets:
- v2/en_speaker_0 through v2/en_speaker_9 (English)
- v2/zh_speaker_0 through v2/zh_speaker_9 (Chinese)
- v2/fr_speaker_0 through v2/fr_speaker_9 (French)
- And many more languages...
"""

import logging
from pathlib import Path
from typing import Any

from ..base import PluginCategory, PluginMetadata

logger = logging.getLogger(__name__)


class BarkPlugin:
    """
    Bark text-to-speech plugin.

    Provides local speech synthesis using Suno's Bark model
    with realistic voice generation and emotional expression.
    """

    def __init__(
        self,
        voice_preset: str = "v2/en_speaker_6",
        use_small_models: bool = True,
        device: str = "auto",
    ):
        """
        Initialize Bark plugin.

        Args:
            voice_preset: Voice preset to use (e.g., "v2/en_speaker_6")
            use_small_models: Use smaller models for faster generation
            device: Device to use (cpu, cuda, auto)
        """
        self.voice_preset = voice_preset
        self.use_small_models = use_small_models
        self.device = device

        self.metadata = PluginMetadata(
            name="bark",
            version="1.0.0",
            category=PluginCategory.AUDIO,
            description="Bark text-to-speech synthesis",
            author="GerdsenAI Team",
            dependencies=["bark", "scipy", "numpy"],
            capabilities=[
                "text_to_speech",
                "speech_synthesis",
                "multi_voice",
                "emotional_speech",
                "non_verbal_sounds",
                "multi_language",
            ],
            configuration={
                "enabled": True,
                "voice_preset": voice_preset,
                "use_small_models": use_small_models,
                "device": device,
                "sample_rate": 24000,  # Bark's native sample rate
            }
        )
        self._initialized = False
        self._bark_module = None

    async def initialize(self) -> bool:
        """
        Initialize Bark plugin.

        Checks for dependencies and loads the model.

        Returns:
            True if initialization successful
        """
        logger.info("Initializing Bark text-to-speech plugin...")

        try:
            # Import Bark (will download models on first use)
            from bark import SAMPLE_RATE, generate_audio, preload_models
            from bark.generation import ALLOWED_PROMPTS

            self._bark_module = {
                "generate_audio": generate_audio,
                "preload_models": preload_models,
                "SAMPLE_RATE": SAMPLE_RATE,
                "ALLOWED_PROMPTS": ALLOWED_PROMPTS,
            }

            logger.info("Bark module loaded successfully")

            # Set device
            if self.device != "auto":
                import os
                if self.device == "cpu":
                    os.environ["SUNO_USE_SMALL_MODELS"] = "1" if self.use_small_models else "0"
                    os.environ["SUNO_OFFLOAD_CPU"] = "1"
                elif self.device == "cuda":
                    os.environ["SUNO_USE_SMALL_MODELS"] = "1" if self.use_small_models else "0"

            # Preload models (optional, can be slow)
            # logger.info("Preloading Bark models...")
            # preload_models()
            logger.info("Bark models will be loaded on first use")

            self._initialized = True
            logger.info("Bark plugin initialized successfully")
            return True

        except ImportError as e:
            logger.error(
                f"Bark not available: {e}\n"
                "Install with: pip install git+https://github.com/suno-ai/bark.git\n"
                "Also install: pip install scipy numpy"
            )
            return False
        except Exception as e:
            logger.error(f"Failed to initialize Bark plugin: {e}")
            return False

    async def shutdown(self) -> None:
        """
        Cleanup Bark plugin resources.

        Unloads the model to free memory.
        """
        logger.info("Shutting down Bark plugin...")
        self._initialized = False
        self._bark_module = None
        logger.info("Bark plugin shut down")

    async def health_check(self) -> dict[str, Any]:
        """
        Check Bark plugin health.

        Returns:
            Health status dictionary
        """
        if not self._initialized:
            return {
                "status": "unhealthy",
                "message": "Plugin not initialized",
                "details": {}
            }

        return {
            "status": "healthy",
            "message": "Bark plugin operational",
            "details": {
                "voice_preset": self.voice_preset,
                "use_small_models": self.use_small_models,
                "device": self.device,
                "sample_rate": self.metadata.configuration["sample_rate"],
                "capabilities": self.metadata.capabilities,
            }
        }

    async def synthesize(
        self,
        text: str,
        output_path: str | Path | None = None,
        voice_preset: str | None = None,
        temperature: float = 0.7,
    ) -> dict[str, Any]:
        """
        Synthesize speech from text.

        Args:
            text: Text to synthesize (max ~200 words per generation)
            output_path: Optional path to save audio file (.wav)
            voice_preset: Optional voice preset (overrides default)
            temperature: Generation temperature (0.0-1.0, higher = more varied)

        Returns:
            Dictionary with synthesis results:
            - audio_array: Numpy array of audio samples
            - sample_rate: Sample rate (Hz)
            - output_path: Path to saved file (if saved)
            - duration: Audio duration in seconds
            - text: Original text

        Raises:
            RuntimeError: If plugin not initialized
            ValueError: If text is too long or invalid
        """
        if not self._initialized:
            raise RuntimeError("Bark plugin not initialized")

        if not text or len(text.strip()) == 0:
            raise ValueError("Text cannot be empty")

        # Warn if text is very long (Bark works best with shorter segments)
        word_count = len(text.split())
        if word_count > 200:
            logger.warning(
                f"Text has {word_count} words. Bark works best with <200 words. "
                "Consider splitting into smaller segments."
            )

        voice = voice_preset or self.voice_preset

        logger.info(f"Synthesizing speech: {len(text)} characters")
        logger.info(f"Voice preset: {voice}")
        logger.info(f"Temperature: {temperature}")

        try:
            # Set generation parameters
            import os
            os.environ["SUNO_ENABLE_MPS"] = "0"  # Disable MPS for stability

            # Generate audio
            logger.info("Generating audio with Bark...")
            audio_array = self._bark_module["generate_audio"](
                text,
                history_prompt=voice,
                text_temp=temperature,
                waveform_temp=temperature,
            )

            sample_rate = self._bark_module["SAMPLE_RATE"]
            duration = len(audio_array) / sample_rate

            logger.info(f"Audio generated successfully ({duration:.2f} seconds)")

            # Save to file if requested
            saved_path = None
            if output_path:
                output_path = Path(output_path)

                # Ensure .wav extension
                if output_path.suffix.lower() != ".wav":
                    output_path = output_path.with_suffix(".wav")

                # Create parent directory if needed
                output_path.parent.mkdir(parents=True, exist_ok=True)

                # Write WAV file
                from scipy.io.wavfile import write as write_wav
                write_wav(str(output_path), sample_rate, audio_array)

                saved_path = str(output_path)
                logger.info(f"Audio saved to: {saved_path}")

            return {
                "audio_array": audio_array,
                "sample_rate": sample_rate,
                "output_path": saved_path,
                "duration": duration,
                "text": text,
                "voice_preset": voice,
            }

        except Exception as e:
            logger.error(f"Speech synthesis failed: {e}")
            raise

    async def synthesize_long(
        self,
        text: str,
        output_path: str | Path,
        voice_preset: str | None = None,
        temperature: float = 0.7,
        chunk_size: int = 150,
    ) -> dict[str, Any]:
        """
        Synthesize long text by splitting into chunks.

        Bark works best with shorter segments (~200 words), so this method
        automatically splits long text and concatenates the audio.

        Args:
            text: Long text to synthesize
            output_path: Path to save concatenated audio file
            voice_preset: Optional voice preset
            temperature: Generation temperature
            chunk_size: Maximum words per chunk

        Returns:
            Dictionary with synthesis results
        """
        if not self._initialized:
            raise RuntimeError("Bark plugin not initialized")

        # Split text into sentences
        sentences = text.replace("\n", " ").split(".")
        sentences = [s.strip() + "." for s in sentences if s.strip()]

        # Group sentences into chunks
        chunks = []
        current_chunk = []
        current_word_count = 0

        for sentence in sentences:
            sentence_words = len(sentence.split())

            if current_word_count + sentence_words > chunk_size and current_chunk:
                chunks.append(" ".join(current_chunk))
                current_chunk = [sentence]
                current_word_count = sentence_words
            else:
                current_chunk.append(sentence)
                current_word_count += sentence_words

        if current_chunk:
            chunks.append(" ".join(current_chunk))

        logger.info(f"Split text into {len(chunks)} chunks")

        # Generate audio for each chunk
        import numpy as np

        audio_segments = []
        total_duration = 0

        for i, chunk in enumerate(chunks, 1):
            logger.info(f"Generating chunk {i}/{len(chunks)}")

            result = await self.synthesize(
                text=chunk,
                voice_preset=voice_preset,
                temperature=temperature,
            )

            audio_segments.append(result["audio_array"])
            total_duration += result["duration"]

        # Concatenate audio segments
        logger.info("Concatenating audio segments...")
        full_audio = np.concatenate(audio_segments)

        # Save to file
        output_path = Path(output_path)
        if output_path.suffix.lower() != ".wav":
            output_path = output_path.with_suffix(".wav")

        output_path.parent.mkdir(parents=True, exist_ok=True)

        from scipy.io.wavfile import write as write_wav
        sample_rate = self._bark_module["SAMPLE_RATE"]
        write_wav(str(output_path), sample_rate, full_audio)

        logger.info(f"Long audio saved to: {output_path}")
        logger.info(f"Total duration: {total_duration:.2f} seconds")

        return {
            "audio_array": full_audio,
            "sample_rate": sample_rate,
            "output_path": str(output_path),
            "duration": total_duration,
            "text": text,
            "chunks": len(chunks),
            "voice_preset": voice_preset or self.voice_preset,
        }

    def get_available_voices(self) -> dict[str, list[str]]:
        """
        Get list of available voice presets by language.

        Returns:
            Dictionary mapping language codes to voice preset lists
        """
        # Common voice presets (Bark supports many more)
        voices = {
            "en": [f"v2/en_speaker_{i}" for i in range(10)],
            "zh": [f"v2/zh_speaker_{i}" for i in range(10)],
            "fr": [f"v2/fr_speaker_{i}" for i in range(5)],
            "de": [f"v2/de_speaker_{i}" for i in range(5)],
            "es": [f"v2/es_speaker_{i}" for i in range(5)],
            "it": [f"v2/it_speaker_{i}" for i in range(5)],
            "pt": [f"v2/pt_speaker_{i}" for i in range(5)],
            "pl": [f"v2/pl_speaker_{i}" for i in range(5)],
            "tr": [f"v2/tr_speaker_{i}" for i in range(5)],
            "ru": [f"v2/ru_speaker_{i}" for i in range(5)],
            "nl": [f"v2/nl_speaker_{i}" for i in range(5)],
            "ja": [f"v2/ja_speaker_{i}" for i in range(5)],
            "ko": [f"v2/ko_speaker_{i}" for i in range(5)],
        }
        return voices


# Export plugin class for auto-discovery
__all__ = ["BarkPlugin"]
