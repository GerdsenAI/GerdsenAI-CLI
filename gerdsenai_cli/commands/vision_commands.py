"""
Vision Commands for GerdsenAI CLI.

Provides CLI commands for image understanding and OCR capabilities.
"""

import logging
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from ..plugins.base import PluginCategory
from ..plugins.registry import plugin_registry
from ..utils.display import show_info
from .base import BaseCommand, CommandArgument, CommandCategory, CommandResult

logger = logging.getLogger(__name__)
console = Console()


class ImageCommand(BaseCommand):
    """
    Analyze image content using LLaVA vision model.

    Examples:
        /image screenshot.png
        /image photo.jpg "What objects are in this image?"
        /image diagram.png "Explain this diagram" model=llava:13b
    """

    @property
    def name(self) -> str:
        return "image"

    @property
    def description(self) -> str:
        return "Analyze image content using LLaVA vision model"

    @property
    def category(self) -> CommandCategory:
        return CommandCategory.VISION

    @property
    def aliases(self) -> list[str]:
        return ["img", "vision"]

    def _define_arguments(self) -> dict[str, CommandArgument]:
        return {
            "image_path": CommandArgument(
                name="image_path",
                description="Path to image file",
                required=True,
                arg_type=str,
            ),
            "prompt": CommandArgument(
                name="prompt",
                description="Optional question about the image",
                required=False,
                arg_type=str,
                default="Describe this image in detail.",
            ),
            "model": CommandArgument(
                name="model",
                description="Specific LLaVA model to use",
                required=False,
                arg_type=str,
                default=None,
            ),
            "temperature": CommandArgument(
                name="temperature",
                description="Sampling temperature (0.0-1.0)",
                required=False,
                arg_type=float,
                default=0.7,
            ),
        }

    async def execute(
        self, args: dict[str, Any], context: dict[str, Any]
    ) -> CommandResult:
        """Execute image analysis command."""
        image_path = args["image_path"]
        prompt = args["prompt"]
        model = args.get("model")
        temperature = args.get("temperature", 0.7)

        try:
            # Validate image file exists
            path = Path(image_path)
            if not path.exists():
                return CommandResult(
                    success=False, message=f"❌ Image file not found: {image_path}"
                )

            if not path.is_file():
                return CommandResult(
                    success=False, message=f"❌ Path is not a file: {image_path}"
                )

            # Get LLaVA plugin
            try:
                llava_plugin = plugin_registry.get(PluginCategory.VISION, "llava")
            except KeyError:
                return CommandResult(
                    success=False,
                    message=(
                        "❌ LLaVA plugin not available\n\n"
                        "**Setup Instructions:**\n"
                        "1. Install Ollama: https://ollama.ai\n"
                        "2. Pull LLaVA model: `ollama pull llava`\n"
                        "3. Restart GerdsenAI CLI"
                    ),
                )

            # Initialize plugin if needed
            plugin_id = f"{PluginCategory.VISION.value}.llava"
            if plugin_id not in plugin_registry._initialized_plugins:
                show_info("Initializing LLaVA plugin...")
                success = await plugin_registry.initialize_plugin(
                    PluginCategory.VISION, "llava"
                )
                if not success:
                    return CommandResult(
                        success=False, message="❌ Failed to initialize LLaVA plugin"
                    )

            # Show processing message
            console.print(f"\n🖼️  Analyzing image: [cyan]{path.name}[/cyan]")
            console.print(f"📝 Prompt: [yellow]{prompt}[/yellow]")
            if model:
                console.print(f"🤖 Model: [blue]{model}[/blue]")
            console.print()

            # Analyze image
            response = await llava_plugin.understand_image(
                image=path,
                prompt=prompt,
                model=model,
                temperature=temperature,
            )

            # Display response in a panel
            console.print(
                Panel(
                    Markdown(response),
                    title="🎨 LLaVA Analysis",
                    border_style="green",
                    padding=(1, 2),
                )
            )

            return CommandResult(
                success=True, data={"response": response, "image_path": str(path)}
            )

        except Exception as e:
            logger.error(f"Image analysis failed: {e}", exc_info=True)
            return CommandResult(
                success=False, message=f"❌ Image analysis failed: {e}"
            )


class OCRCommand(BaseCommand):
    """
    Extract text from image using OCR.

    Attempts to use Tesseract OCR first for best accuracy,
    falls back to LLaVA if Tesseract is not available.

    Examples:
        /ocr document.png
        /ocr receipt.jpg languages=en,es
        /ocr screenshot.png confidence=true
    """

    @property
    def name(self) -> str:
        return "ocr"

    @property
    def description(self) -> str:
        return "Extract text from image using OCR"

    @property
    def category(self) -> CommandCategory:
        return CommandCategory.VISION

    @property
    def aliases(self) -> list[str]:
        return ["extract", "text"]

    def _define_arguments(self) -> dict[str, CommandArgument]:
        return {
            "image_path": CommandArgument(
                name="image_path",
                description="Path to image file",
                required=True,
                arg_type=str,
            ),
            "languages": CommandArgument(
                name="languages",
                description="Comma-separated language codes (e.g., en,es,fr)",
                required=False,
                arg_type=str,
                default="en",
            ),
            "confidence": CommandArgument(
                name="confidence",
                description="Return confidence scores",
                required=False,
                arg_type=bool,
                default=False,
            ),
            "use_llava": CommandArgument(
                name="use_llava",
                description="Force use of LLaVA instead of Tesseract",
                required=False,
                arg_type=bool,
                default=False,
            ),
        }

    async def execute(
        self, args: dict[str, Any], context: dict[str, Any]
    ) -> CommandResult:
        """Execute OCR command."""
        image_path = args["image_path"]
        languages_str = args.get("languages", "en")
        return_confidence = args.get("confidence", False)
        use_llava = args.get("use_llava", False)

        # Parse languages
        languages = [lang.strip() for lang in languages_str.split(",")]

        try:
            # Validate image file exists
            path = Path(image_path)
            if not path.exists():
                return CommandResult(
                    success=False, message=f"❌ Image file not found: {image_path}"
                )

            if not path.is_file():
                return CommandResult(
                    success=False, message=f"❌ Path is not a file: {image_path}"
                )

            # Show processing message
            console.print(f"\n📄 Extracting text from: [cyan]{path.name}[/cyan]")
            console.print(f"🌐 Languages: [yellow]{', '.join(languages)}[/yellow]")
            console.print()

            extracted_text = None
            method_used = None

            # Try Tesseract first (unless LLaVA is forced)
            if not use_llava:
                try:
                    tesseract_plugin = plugin_registry.get(
                        PluginCategory.VISION, "tesseract_ocr"
                    )

                    # Initialize if needed
                    plugin_id = f"{PluginCategory.VISION.value}.tesseract_ocr"
                    if plugin_id not in plugin_registry._initialized_plugins:
                        show_info("Initializing Tesseract OCR plugin...")
                        success = await plugin_registry.initialize_plugin(
                            PluginCategory.VISION, "tesseract_ocr"
                        )
                        if success:
                            console.print("✅ Using Tesseract OCR\n")
                            result = await tesseract_plugin.ocr(
                                image=path,
                                languages=languages,
                                return_confidence=return_confidence,
                            )

                            if return_confidence:
                                extracted_text = result["text"]
                                confidence = result["confidence"]
                                method_used = (
                                    f"Tesseract (confidence: {confidence:.1f}%)"
                                )
                            else:
                                extracted_text = result
                                method_used = "Tesseract"

                except (KeyError, RuntimeError) as e:
                    logger.debug(f"Tesseract not available: {e}")
                    # Fall through to LLaVA

            # Fall back to LLaVA if Tesseract failed or was skipped
            if extracted_text is None:
                try:
                    llava_plugin = plugin_registry.get(PluginCategory.VISION, "llava")

                    # Initialize if needed
                    plugin_id = f"{PluginCategory.VISION.value}.llava"
                    if plugin_id not in plugin_registry._initialized_plugins:
                        show_info("Initializing LLaVA plugin...")
                        success = await plugin_registry.initialize_plugin(
                            PluginCategory.VISION, "llava"
                        )
                        if not success:
                            return CommandResult(
                                success=False, message="❌ No OCR engine available"
                            )

                    console.print("✅ Using LLaVA OCR\n")
                    extracted_text = await llava_plugin.ocr(
                        image=path,
                        languages=languages,
                    )
                    method_used = "LLaVA (AI-based)"

                except KeyError:
                    return CommandResult(
                        success=False,
                        message=(
                            "❌ No OCR engine available\n\n"
                            "**Setup Instructions:**\n"
                            "1. **Tesseract** (recommended):\n"
                            "   - Ubuntu/Debian: `sudo apt install tesseract-ocr`\n"
                            "   - macOS: `brew install tesseract`\n"
                            "   - Python: `pip install pytesseract pillow`\n\n"
                            "2. **LLaVA** (fallback):\n"
                            "   - Install Ollama: https://ollama.ai\n"
                            "   - Pull model: `ollama pull llava`\n\n"
                            "Then restart GerdsenAI CLI"
                        ),
                    )

            # Display extracted text
            if extracted_text:
                console.print(
                    Panel(
                        extracted_text,
                        title=f"📝 Extracted Text ({method_used})",
                        border_style="cyan",
                        padding=(1, 2),
                    )
                )

                # Show stats
                word_count = len(extracted_text.split())
                char_count = len(extracted_text)
                console.print(
                    f"\n📊 Stats: {word_count} words, {char_count} characters"
                )

                return CommandResult(
                    success=True,
                    data={
                        "text": extracted_text,
                        "method": method_used,
                        "word_count": word_count,
                        "char_count": char_count,
                    },
                )
            else:
                return CommandResult(
                    success=False, message="❌ No text extracted from image"
                )

        except Exception as e:
            logger.error(f"OCR failed: {e}", exc_info=True)
            return CommandResult(success=False, message=f"❌ OCR failed: {e}")


class VisionStatusCommand(BaseCommand):
    """
    Check status of vision plugins and capabilities.

    Shows which vision models are available and their status.

    Examples:
        /vision-status
        /vstatus
    """

    @property
    def name(self) -> str:
        return "vision-status"

    @property
    def description(self) -> str:
        return "Check vision plugins status"

    @property
    def category(self) -> CommandCategory:
        return CommandCategory.VISION

    @property
    def aliases(self) -> list[str]:
        return ["vstatus", "vision-info"]

    async def execute(
        self, args: dict[str, Any], context: dict[str, Any]
    ) -> CommandResult:
        """Execute vision status command."""
        from rich.table import Table

        try:
            # Get vision plugins
            vision_plugins = plugin_registry.list_plugins(PluginCategory.VISION)

            if not vision_plugins:
                return CommandResult(
                    success=False, message="❌ No vision plugins registered"
                )

            # Create status table
            table = Table(title="🎨 Vision Capabilities", show_header=True)
            table.add_column("Plugin", style="cyan")
            table.add_column("Status", style="yellow")
            table.add_column("Capabilities", style="green")
            table.add_column("Version", style="blue")

            for plugin_meta in vision_plugins:
                # Check if initialized
                plugin_id = f"{PluginCategory.VISION.value}.{plugin_meta.name}"
                is_initialized = plugin_id in plugin_registry._initialized_plugins

                # Try to get health status
                status_emoji = "✅" if is_initialized else "⏸️"
                status_text = "Active" if is_initialized else "Not Initialized"

                if is_initialized:
                    try:
                        plugin = plugin_registry.get(
                            PluginCategory.VISION, plugin_meta.name
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
                1
                for pm in vision_plugins
                if f"{PluginCategory.VISION.value}.{pm.name}"
                in plugin_registry._initialized_plugins
            )

            if initialized_count == 0:
                console.print(
                    Panel(
                        "**Setup Vision Capabilities:**\n\n"
                        "1. **LLaVA** (Image Understanding):\n"
                        "   ```\n"
                        "   ollama pull llava\n"
                        "   ```\n\n"
                        "2. **Tesseract** (OCR):\n"
                        "   ```\n"
                        "   # Ubuntu/Debian\n"
                        "   sudo apt install tesseract-ocr\n"
                        "   pip install pytesseract pillow\n\n"
                        "   # macOS\n"
                        "   brew install tesseract\n"
                        "   pip install pytesseract pillow\n"
                        "   ```",
                        title="🔧 Setup Guide",
                        border_style="yellow",
                    )
                )

            return CommandResult(
                success=True, data={"plugins": [pm.name for pm in vision_plugins]}
            )

        except Exception as e:
            logger.error(f"Vision status check failed: {e}", exc_info=True)
            return CommandResult(success=False, message=f"❌ Status check failed: {e}")


# Export commands
__all__ = ["ImageCommand", "OCRCommand", "VisionStatusCommand"]
