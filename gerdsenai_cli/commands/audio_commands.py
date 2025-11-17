"""
Audio Commands for GerdsenAI CLI.

Provides CLI commands for speech-to-text and text-to-speech capabilities.
"""

import logging
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from .base import BaseCommand, CommandArgument, CommandCategory, CommandResult
from ..plugins.registry import plugin_registry
from ..plugins.base import PluginCategory
from ..utils.display import show_error, show_info, show_success

logger = logging.getLogger(__name__)
console = Console()


class TranscribeCommand(BaseCommand):
    """
    Transcribe audio to text using Whisper.

    Supports 99 languages and various audio formats (mp3, wav, m4a, etc.).

    Examples:
        /transcribe audio.mp3
        /transcribe interview.wav language=en timestamps=true
        /transcribe podcast.m4a task=translate
    """

    @property
    def name(self) -> str:
        return "transcribe"

    @property
    def description(self) -> str:
        return "Transcribe audio to text using Whisper"

    @property
    def category(self) -> CommandCategory:
        return CommandCategory.AUDIO

    @property
    def aliases(self) -> list[str]:
        return ["stt", "speech-to-text"]

    def _define_arguments(self) -> dict[str, CommandArgument]:
        return {
            "audio_path": CommandArgument(
                name="audio_path",
                description="Path to audio file (mp3, wav, m4a, etc.)",
                required=True,
                arg_type=str,
            ),
            "language": CommandArgument(
                name="language",
                description="Language code (e.g., en, es, fr) or None for auto-detect",
                required=False,
                arg_type=str,
                default=None,
            ),
            "task": CommandArgument(
                name="task",
                description="Task: 'transcribe' or 'translate' (to English)",
                required=False,
                arg_type=str,
                choices=["transcribe", "translate"],
                default="transcribe",
            ),
            "timestamps": CommandArgument(
                name="timestamps",
                description="Include word-level timestamps",
                required=False,
                arg_type=bool,
                default=False,
            ),
        }

    async def execute(
        self, args: dict[str, Any], context: dict[str, Any]
    ) -> CommandResult:
        """Execute transcription command."""
        audio_path = args["audio_path"]
        language = args.get("language")
        task = args.get("task", "transcribe")
        timestamps = args.get("timestamps", False)

        try:
            # Validate audio file exists
            path = Path(audio_path)
            if not path.exists():
                return CommandResult(
                    success=False,
                    message=f"❌ Audio file not found: {audio_path}"
                )

            if not path.is_file():
                return CommandResult(
                    success=False,
                    message=f"❌ Path is not a file: {audio_path}"
                )

            # Get Whisper plugin
            try:
                whisper_plugin = plugin_registry.get(PluginCategory.AUDIO, "whisper")
            except KeyError:
                return CommandResult(
                    success=False,
                    message=(
                        "❌ Whisper plugin not available\n\n"
                        "**Setup Instructions:**\n"
                        "1. Install ffmpeg:\n"
                        "   - Ubuntu/Debian: `sudo apt install ffmpeg`\n"
                        "   - macOS: `brew install ffmpeg`\n"
                        "2. Install Whisper:\n"
                        "   - Recommended: `pip install faster-whisper`\n"
                        "   - Alternative: `pip install openai-whisper`\n"
                        "3. Restart GerdsenAI CLI"
                    )
                )

            # Initialize plugin if needed
            plugin_id = f"{PluginCategory.AUDIO.value}.whisper"
            if plugin_id not in plugin_registry._initialized_plugins:
                show_info("Initializing Whisper plugin (first use may download models)...")
                success = await plugin_registry.initialize_plugin(
                    PluginCategory.AUDIO, "whisper"
                )
                if not success:
                    return CommandResult(
                        success=False,
                        message="❌ Failed to initialize Whisper plugin"
                    )

            # Show processing message
            console.print(f"\n🎤 Transcribing audio: [cyan]{path.name}[/cyan]")
            if language:
                console.print(f"🌐 Language: [yellow]{language}[/yellow]")
            console.print(f"📝 Task: [yellow]{task}[/yellow]")
            if timestamps:
                console.print("⏱️  Generating timestamps")
            console.print()
            console.print("⏳ Processing (this may take a moment)...")

            # Transcribe audio
            result = await whisper_plugin.transcribe(
                audio=path,
                language=language,
                task=task,
                return_timestamps=timestamps,
            )

            # Display result
            console.print()
            console.print(Panel(
                result["text"],
                title=f"📝 Transcription ({result['language'].upper()})",
                border_style="cyan",
                padding=(1, 2),
            ))

            # Show metadata
            if result.get("duration"):
                console.print(f"\n⏱️  Duration: {result['duration']:.2f} seconds")
            console.print(f"📊 Characters: {len(result['text'])}")
            console.print(f"📊 Words: {len(result['text'].split())}")

            if result.get("language_probability"):
                console.print(f"🎯 Language confidence: {result['language_probability']:.1%}")

            # Show timestamps if requested
            if timestamps and result.get("segments"):
                console.print(f"\n⏱️  Segments: {len(result['segments'])}")

            return CommandResult(
                success=True,
                data={
                    "text": result["text"],
                    "language": result["language"],
                    "duration": result.get("duration"),
                    "segments": result.get("segments"),
                }
            )

        except Exception as e:
            logger.error(f"Transcription failed: {e}", exc_info=True)
            return CommandResult(
                success=False,
                message=f"❌ Transcription failed: {e}"
            )


class SpeakCommand(BaseCommand):
    """
    Generate speech from text using Bark.

    Supports multiple voices and languages with natural prosody.

    Examples:
        /speak "Hello world!"
        /speak "Bonjour le monde" voice=v2/fr_speaker_1 output=greeting.wav
        /speak "こんにちは世界" voice=v2/ja_speaker_0
    """

    @property
    def name(self) -> str:
        return "speak"

    @property
    def description(self) -> str:
        return "Generate speech from text using Bark"

    @property
    def category(self) -> CommandCategory:
        return CommandCategory.AUDIO

    @property
    def aliases(self) -> list[str]:
        return ["tts", "text-to-speech"]

    def _define_arguments(self) -> dict[str, CommandArgument]:
        return {
            "text": CommandArgument(
                name="text",
                description="Text to synthesize (max ~200 words)",
                required=True,
                arg_type=str,
            ),
            "output": CommandArgument(
                name="output",
                description="Output file path (.wav)",
                required=False,
                arg_type=str,
                default=None,
            ),
            "voice": CommandArgument(
                name="voice",
                description="Voice preset (e.g., v2/en_speaker_6)",
                required=False,
                arg_type=str,
                default=None,
            ),
            "temperature": CommandArgument(
                name="temperature",
                description="Generation temperature (0.0-1.0)",
                required=False,
                arg_type=float,
                default=0.7,
            ),
        }

    async def execute(
        self, args: dict[str, Any], context: dict[str, Any]
    ) -> CommandResult:
        """Execute speech synthesis command."""
        text = args["text"]
        output = args.get("output")
        voice = args.get("voice")
        temperature = args.get("temperature", 0.7)

        try:
            # Validate text
            if not text or len(text.strip()) == 0:
                return CommandResult(
                    success=False,
                    message="❌ Text cannot be empty"
                )

            word_count = len(text.split())
            if word_count > 200:
                console.print(
                    f"⚠️  Warning: Text has {word_count} words. "
                    "Bark works best with <200 words."
                )

            # Get Bark plugin
            try:
                bark_plugin = plugin_registry.get(PluginCategory.AUDIO, "bark")
            except KeyError:
                return CommandResult(
                    success=False,
                    message=(
                        "❌ Bark plugin not available\n\n"
                        "**Setup Instructions:**\n"
                        "1. Install Bark:\n"
                        "   `pip install git+https://github.com/suno-ai/bark.git`\n"
                        "2. Install dependencies:\n"
                        "   `pip install scipy numpy`\n"
                        "3. Restart GerdsenAI CLI\n\n"
                        "Note: First use will download ~2-10GB of models"
                    )
                )

            # Initialize plugin if needed
            plugin_id = f"{PluginCategory.AUDIO.value}.bark"
            if plugin_id not in plugin_registry._initialized_plugins:
                show_info("Initializing Bark plugin (first use will download models)...")
                success = await plugin_registry.initialize_plugin(
                    PluginCategory.AUDIO, "bark"
                )
                if not success:
                    return CommandResult(
                        success=False,
                        message="❌ Failed to initialize Bark plugin"
                    )

            # Show processing message
            console.print(f"\n🔊 Generating speech...")
            console.print(f"📝 Text: [yellow]{text[:100]}{'...' if len(text) > 100 else ''}[/yellow]")
            if voice:
                console.print(f"🎙️  Voice: [cyan]{voice}[/cyan]")
            console.print(f"🌡️  Temperature: {temperature}")
            console.print()
            console.print("⏳ Processing (this may take 10-60 seconds)...")

            # Generate speech
            result = await bark_plugin.synthesize(
                text=text,
                output_path=output,
                voice_preset=voice,
                temperature=temperature,
            )

            # Display result
            console.print()
            if result["output_path"]:
                console.print(f"✅ Speech saved to: [green]{result['output_path']}[/green]")
            else:
                console.print("✅ Speech generated (audio array in memory)")

            console.print(f"\n⏱️  Duration: {result['duration']:.2f} seconds")
            console.print(f"📊 Sample rate: {result['sample_rate']} Hz")
            console.print(f"🎙️  Voice: {result['voice_preset']}")

            return CommandResult(
                success=True,
                data={
                    "output_path": result["output_path"],
                    "duration": result["duration"],
                    "sample_rate": result["sample_rate"],
                    "voice_preset": result["voice_preset"],
                }
            )

        except Exception as e:
            logger.error(f"Speech synthesis failed: {e}", exc_info=True)
            return CommandResult(
                success=False,
                message=f"❌ Speech synthesis failed: {e}"
            )


class AudioStatusCommand(BaseCommand):
    """
    Check status of audio plugins and capabilities.

    Shows which audio models are available and their status.

    Examples:
        /audio-status
        /astatus
    """

    @property
    def name(self) -> str:
        return "audio-status"

    @property
    def description(self) -> str:
        return "Check audio plugins status"

    @property
    def category(self) -> CommandCategory:
        return CommandCategory.AUDIO

    @property
    def aliases(self) -> list[str]:
        return ["astatus", "audio-info"]

    async def execute(
        self, args: dict[str, Any], context: dict[str, Any]
    ) -> CommandResult:
        """Execute audio status command."""
        from rich.table import Table

        try:
            # Get audio plugins
            audio_plugins = plugin_registry.list_plugins(PluginCategory.AUDIO)

            if not audio_plugins:
                return CommandResult(
                    success=False,
                    message="❌ No audio plugins registered"
                )

            # Create status table
            table = Table(title="🎤 Audio Capabilities", show_header=True)
            table.add_column("Plugin", style="cyan")
            table.add_column("Status", style="yellow")
            table.add_column("Capabilities", style="green")
            table.add_column("Version", style="blue")

            for plugin_meta in audio_plugins:
                # Check if initialized
                plugin_id = f"{PluginCategory.AUDIO.value}.{plugin_meta.name}"
                is_initialized = plugin_id in plugin_registry._initialized_plugins

                # Try to get health status
                status_emoji = "✅" if is_initialized else "⏸️"
                status_text = "Active" if is_initialized else "Not Initialized"

                if is_initialized:
                    try:
                        plugin = plugin_registry.get(
                            PluginCategory.AUDIO, plugin_meta.name
                        )
                        health = await plugin.health_check()
                        if health["status"] != "healthy":
                            status_emoji = "⚠️"
                            status_text = health["status"].capitalize()
                    except Exception:
                        status_emoji = "❌"
                        status_text = "Error"

                # Format capabilities
                caps = ", ".join(plugin_meta.capabilities[:3])
                if len(plugin_meta.capabilities) > 3:
                    caps += f" +{len(plugin_meta.capabilities) - 3} more"

                table.add_row(
                    plugin_meta.name,
                    f"{status_emoji} {status_text}",
                    caps,
                    plugin_meta.version,
                )

            console.print("\n")
            console.print(table)
            console.print()

            # Show setup instructions if no plugins initialized
            initialized_count = sum(
                1 for pm in audio_plugins
                if f"{PluginCategory.AUDIO.value}.{pm.name}" in plugin_registry._initialized_plugins
            )

            if initialized_count == 0:
                console.print(Panel(
                    "**Setup Audio Capabilities:**\n\n"
                    "1. **Whisper** (Speech-to-Text):\n"
                    "   ```\n"
                    "   # Ubuntu/Debian\n"
                    "   sudo apt install ffmpeg\n"
                    "   pip install faster-whisper\n\n"
                    "   # macOS\n"
                    "   brew install ffmpeg\n"
                    "   pip install faster-whisper\n"
                    "   ```\n\n"
                    "2. **Bark** (Text-to-Speech):\n"
                    "   ```\n"
                    "   pip install git+https://github.com/suno-ai/bark.git\n"
                    "   pip install scipy numpy\n"
                    "   ```",
                    title="🔧 Setup Guide",
                    border_style="yellow",
                ))

            return CommandResult(
                success=True,
                data={"plugins": [pm.name for pm in audio_plugins]}
            )

        except Exception as e:
            logger.error(f"Audio status check failed: {e}", exc_info=True)
            return CommandResult(
                success=False,
                message=f"❌ Status check failed: {e}"
            )


# Export commands
__all__ = ["TranscribeCommand", "SpeakCommand", "AudioStatusCommand"]
