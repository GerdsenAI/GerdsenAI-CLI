"""
Tesseract OCR Plugin for GerdsenAI CLI.

Integrates Tesseract OCR for robust text extraction from images.

Tesseract is a mature, open-source OCR engine originally developed by HP
and now maintained by Google. It supports 100+ languages and provides
excellent accuracy for printed text.

Requirements:
- tesseract-ocr system package installed
- pytesseract Python package: pip install pytesseract pillow

Installation:
- Ubuntu/Debian: sudo apt install tesseract-ocr
- macOS: brew install tesseract
- Windows: https://github.com/UB-Mannheim/tesseract/wiki

For additional languages:
- Ubuntu/Debian: sudo apt install tesseract-ocr-[lang]
- macOS: brew install tesseract-lang
"""

import logging
import shutil
from pathlib import Path
from typing import Any

from ..base import PluginCategory, PluginMetadata

logger = logging.getLogger(__name__)


class TesseractOCRPlugin:
    """
    Tesseract OCR plugin for text extraction.

    Provides production-grade OCR capabilities using Tesseract engine.
    More accurate than LLaVA for text-heavy documents.
    """

    def __init__(
        self,
        default_lang: str = "eng",
        config: str = "--psm 3"
    ):
        """
        Initialize Tesseract OCR plugin.

        Args:
            default_lang: Default language code (e.g., "eng", "spa", "fra")
            config: Tesseract configuration string (PSM modes, OEM, etc.)
        """
        self.default_lang = default_lang
        self.config = config

        self.metadata = PluginMetadata(
            name="tesseract_ocr",
            version="1.0.0",
            category=PluginCategory.VISION,
            description="Tesseract OCR for text extraction from images",
            author="GerdsenAI Team",
            dependencies=["pytesseract", "pillow"],
            capabilities=[
                "ocr",
                "text_extraction",
                "multi_language",
                "layout_analysis",
                "confidence_scores",
            ],
            configuration={
                "enabled": True,
                "default_lang": default_lang,
                "config": config,
                "psm_modes": {
                    "0": "Orientation and script detection (OSD) only",
                    "1": "Automatic page segmentation with OSD",
                    "3": "Fully automatic page segmentation (default)",
                    "4": "Assume a single column of text",
                    "6": "Assume a single uniform block of text",
                    "11": "Sparse text - find as much text as possible",
                    "13": "Raw line - treat image as single text line",
                },
            }
        )
        self._initialized = False
        self._tesseract_available = False
        self._available_languages: list[str] = []

        # Lazy imports
        self._pytesseract = None
        self._PIL_Image = None

    async def initialize(self) -> bool:
        """
        Initialize Tesseract OCR plugin.

        Checks if Tesseract is installed and available.

        Returns:
            True if initialization successful
        """
        logger.info("Initializing Tesseract OCR plugin...")

        try:
            # Check if tesseract binary is available
            tesseract_path = shutil.which("tesseract")
            if not tesseract_path:
                logger.error(
                    "Tesseract not found. Install with:\n"
                    "  Ubuntu/Debian: sudo apt install tesseract-ocr\n"
                    "  macOS: brew install tesseract\n"
                    "  Windows: https://github.com/UB-Mannheim/tesseract/wiki"
                )
                return False

            logger.info(f"Found Tesseract at: {tesseract_path}")

            # Import pytesseract (lazy import)
            try:
                import pytesseract
                from PIL import Image

                self._pytesseract = pytesseract
                self._PIL_Image = Image

            except ImportError as e:
                logger.error(
                    f"Required Python packages not found: {e}\n"
                    "Install with: pip install pytesseract pillow"
                )
                return False

            # Get available languages
            try:
                langs_output = self._pytesseract.get_languages()
                self._available_languages = langs_output
                logger.info(f"Available languages: {', '.join(self._available_languages[:10])}...")

                # Check if default language is available
                if self.default_lang not in self._available_languages:
                    logger.warning(
                        f"Default language '{self.default_lang}' not available. "
                        f"Using first available: {self._available_languages[0]}"
                    )
                    self.default_lang = self._available_languages[0]

            except Exception as e:
                logger.warning(f"Could not get language list: {e}")
                self._available_languages = ["eng"]  # Fallback

            self._tesseract_available = True
            self._initialized = True
            logger.info("Tesseract OCR plugin initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize Tesseract OCR plugin: {e}")
            return False

    async def shutdown(self) -> None:
        """
        Cleanup Tesseract OCR plugin resources.

        Tesseract is a system binary, so no local cleanup needed.
        """
        logger.info("Shutting down Tesseract OCR plugin...")
        self._initialized = False
        self._tesseract_available = False
        self._available_languages = []
        logger.info("Tesseract OCR plugin shut down")

    async def health_check(self) -> dict[str, Any]:
        """
        Check Tesseract OCR plugin health.

        Returns:
            Health status dictionary
        """
        if not self._initialized:
            return {
                "status": "unhealthy",
                "message": "Plugin not initialized",
                "details": {}
            }

        # Check if Tesseract is still available
        tesseract_path = shutil.which("tesseract")
        if not tesseract_path:
            return {
                "status": "unhealthy",
                "message": "Tesseract binary not found",
                "details": {}
            }

        return {
            "status": "healthy",
            "message": "Tesseract OCR plugin operational",
            "details": {
                "tesseract_path": tesseract_path,
                "default_lang": self.default_lang,
                "available_languages": self._available_languages[:20],  # Limit output
                "capabilities": self.metadata.capabilities,
            }
        }

    async def ocr(
        self,
        image: str | Path | bytes,
        languages: list[str] = ["en"],
        config: str | None = None,
        return_confidence: bool = False,
    ) -> str | dict[str, Any]:
        """
        Extract text from image using Tesseract OCR.

        Args:
            image: Image file path, Path object, or raw bytes
            languages: List of language codes (e.g., ["en"], ["en", "es"])
            config: Optional Tesseract config string (overrides default)
            return_confidence: If True, return dict with text and confidence

        Returns:
            Extracted text string, or dict with text and confidence if requested

        Raises:
            RuntimeError: If plugin not initialized
            ValueError: If image format is invalid
            FileNotFoundError: If image file doesn't exist
        """
        if not self._initialized:
            raise RuntimeError("Tesseract OCR plugin not initialized")

        # Convert language codes (en -> eng, es -> spa, etc.)
        lang_codes = self._convert_language_codes(languages)
        lang_string = "+".join(lang_codes)

        # Use provided config or default
        config_string = config or self.config

        logger.info(f"Performing OCR with languages: {lang_string}")

        try:
            # Load image
            if isinstance(image, bytes):
                # Convert bytes to PIL Image
                from io import BytesIO
                img = self._PIL_Image.open(BytesIO(image))
            elif isinstance(image, (str, Path)):
                path = Path(image)
                if not path.exists():
                    raise FileNotFoundError(f"Image file not found: {path}")
                if not path.is_file():
                    raise ValueError(f"Path is not a file: {path}")
                img = self._PIL_Image.open(path)
            else:
                raise ValueError(f"Invalid image type: {type(image)}")

            # Perform OCR
            if return_confidence:
                # Get detailed data with confidence scores
                data = self._pytesseract.image_to_data(
                    img,
                    lang=lang_string,
                    config=config_string,
                    output_type=self._pytesseract.Output.DICT
                )

                # Extract text and calculate average confidence
                texts = [
                    data["text"][i]
                    for i in range(len(data["text"]))
                    if int(data["conf"][i]) > 0  # Filter out low confidence
                ]
                confidences = [
                    int(data["conf"][i])
                    for i in range(len(data["conf"]))
                    if int(data["conf"][i]) > 0
                ]

                text = " ".join(texts)
                avg_confidence = sum(confidences) / len(confidences) if confidences else 0

                logger.info(f"OCR complete - Average confidence: {avg_confidence:.1f}%")

                return {
                    "text": text,
                    "confidence": avg_confidence,
                    "word_count": len(texts),
                    "languages": lang_codes,
                }
            else:
                # Simple text extraction
                text = self._pytesseract.image_to_string(
                    img,
                    lang=lang_string,
                    config=config_string
                )

                logger.info(f"OCR complete - Extracted {len(text)} characters")
                return text.strip()

        except Exception as e:
            logger.error(f"OCR failed: {e}")
            raise

    def _convert_language_codes(self, languages: list[str]) -> list[str]:
        """
        Convert ISO 639-1 language codes to Tesseract codes.

        Args:
            languages: List of ISO 639-1 codes (e.g., ["en", "es"])

        Returns:
            List of Tesseract language codes (e.g., ["eng", "spa"])
        """
        # Common language code mappings
        code_map = {
            "en": "eng",
            "es": "spa",
            "fr": "fra",
            "de": "deu",
            "it": "ita",
            "pt": "por",
            "ru": "rus",
            "ja": "jpn",
            "ko": "kor",
            "zh": "chi_sim",
            "ar": "ara",
            "hi": "hin",
        }

        tesseract_codes = []
        for lang in languages:
            # If already a 3-letter code, use as-is
            if len(lang) == 3:
                tesseract_codes.append(lang)
            # If 2-letter code, try to map it
            elif lang in code_map:
                tesseract_codes.append(code_map[lang])
            else:
                # Unknown code, try to use as-is
                logger.warning(f"Unknown language code: {lang}, using as-is")
                tesseract_codes.append(lang)

        # Validate against available languages
        validated = []
        for code in tesseract_codes:
            if code in self._available_languages:
                validated.append(code)
            else:
                logger.warning(
                    f"Language '{code}' not available in Tesseract. "
                    f"Available: {', '.join(self._available_languages[:10])}..."
                )
                # Fall back to default language
                if self.default_lang not in validated:
                    validated.append(self.default_lang)

        return validated if validated else [self.default_lang]

    def get_available_languages(self) -> list[str]:
        """
        Get list of available Tesseract languages.

        Returns:
            List of language codes
        """
        return self._available_languages.copy()

    async def extract_layout(
        self,
        image: str | Path | bytes,
        languages: list[str] = ["en"]
    ) -> dict[str, Any]:
        """
        Extract text with layout information.

        Returns bounding boxes, text, and confidence for each text region.

        Args:
            image: Image file path, Path object, or raw bytes
            languages: List of language codes

        Returns:
            Dictionary with layout information
        """
        if not self._initialized:
            raise RuntimeError("Tesseract OCR plugin not initialized")

        lang_codes = self._convert_language_codes(languages)
        lang_string = "+".join(lang_codes)

        try:
            # Load image
            if isinstance(image, bytes):
                from io import BytesIO
                img = self._PIL_Image.open(BytesIO(image))
            else:
                img = self._PIL_Image.open(image)

            # Get detailed layout data
            data = self._pytesseract.image_to_data(
                img,
                lang=lang_string,
                config=self.config,
                output_type=self._pytesseract.Output.DICT
            )

            # Organize by blocks/lines
            regions = []
            for i in range(len(data["text"])):
                if int(data["conf"][i]) > 0:  # Filter low confidence
                    regions.append({
                        "text": data["text"][i],
                        "confidence": int(data["conf"][i]),
                        "bbox": {
                            "x": data["left"][i],
                            "y": data["top"][i],
                            "width": data["width"][i],
                            "height": data["height"][i],
                        },
                        "block": data["block_num"][i],
                        "line": data["line_num"][i],
                        "word": data["word_num"][i],
                    })

            return {
                "regions": regions,
                "total_text": " ".join([r["text"] for r in regions]),
                "region_count": len(regions),
                "languages": lang_codes,
            }

        except Exception as e:
            logger.error(f"Layout extraction failed: {e}")
            raise


# Export plugin class for auto-discovery
__all__ = ["TesseractOCRPlugin"]
