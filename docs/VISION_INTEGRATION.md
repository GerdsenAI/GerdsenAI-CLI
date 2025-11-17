# Vision Integration Guide

## Overview

GerdsenAI CLI now supports **multimodal AI capabilities** with integrated vision understanding and OCR (Optical Character Recognition). This brings frontier AI capabilities to your local environment, allowing you to:

- **Analyze images** with LLaVA vision models
- **Extract text** from images using Tesseract OCR
- **Ask questions** about visual content
- **Process documents** with text extraction

All vision features run **locally** with open-source models, ensuring privacy and control over your data.

---

## 🎨 Vision Capabilities

### 1. Image Understanding (LLaVA)

**LLaVA** (Large Language and Vision Assistant) is a multimodal AI model that combines vision and language understanding. It can:

- Describe image content in detail
- Answer questions about images
- Identify objects and scenes
- Explain diagrams and visualizations
- Perform basic OCR

**Powered by:** Ollama + LLaVA models

### 2. OCR (Tesseract)

**Tesseract** is a mature, production-grade OCR engine for extracting text from images. It provides:

- High-accuracy text extraction
- Support for 100+ languages
- Layout analysis
- Confidence scores
- Multi-column document support

**Powered by:** Tesseract OCR engine

---

## 🚀 Quick Start

### Prerequisites

#### For Image Understanding (LLaVA)

1. **Install Ollama:**
   ```bash
   # Visit https://ollama.ai for installation
   # Or use package managers:

   # macOS
   brew install ollama

   # Linux
   curl -fsSL https://ollama.ai/install.sh | sh
   ```

2. **Pull LLaVA model:**
   ```bash
   # Recommended: 7B model (good balance of speed and quality)
   ollama pull llava:7b

   # For better quality (requires more VRAM):
   ollama pull llava:13b

   # For highest quality (requires significant VRAM):
   ollama pull llava:34b
   ```

3. **Start Ollama:**
   ```bash
   ollama serve
   ```

#### For OCR (Tesseract)

1. **Install Tesseract:**
   ```bash
   # Ubuntu/Debian
   sudo apt install tesseract-ocr

   # macOS
   brew install tesseract

   # Windows
   # Download from: https://github.com/UB-Mannheim/tesseract/wiki
   ```

2. **Install Python dependencies:**
   ```bash
   pip install pytesseract pillow
   ```

3. **Install additional languages (optional):**
   ```bash
   # Ubuntu/Debian
   sudo apt install tesseract-ocr-spa  # Spanish
   sudo apt install tesseract-ocr-fra  # French
   sudo apt install tesseract-ocr-deu  # German

   # macOS
   brew install tesseract-lang
   ```

---

## 📝 CLI Commands

### `/image` - Analyze Images

Analyze image content using LLaVA vision model.

**Syntax:**
```
/image <image_path> [prompt] [model=<model_name>] [temperature=<0.0-1.0>]
```

**Examples:**

```bash
# Basic image analysis
/image screenshot.png

# Ask specific questions
/image photo.jpg "What objects are in this image?"
/image diagram.png "Explain this diagram in detail"

# Use specific model
/image complex_scene.jpg model=llava:13b

# Adjust creativity
/image artwork.png "Describe the artistic style" temperature=0.9
```

**Aliases:** `/img`, `/vision`

**Options:**
- `prompt` - Question or instruction about the image (default: "Describe this image in detail")
- `model` - Specific LLaVA model to use (default: llava:7b)
- `temperature` - Sampling temperature 0.0-1.0 (default: 0.7)

---

### `/ocr` - Extract Text

Extract text from images using OCR.

**Syntax:**
```
/ocr <image_path> [languages=<lang1,lang2>] [confidence=true|false] [use_llava=true|false]
```

**Examples:**

```bash
# Extract text from image
/ocr document.png

# Multi-language OCR
/ocr receipt.jpg languages=en,es
/ocr menu.png languages=en,fr,de

# Get confidence scores
/ocr scanned_page.png confidence=true

# Force LLaVA OCR (if Tesseract unavailable)
/ocr screenshot.png use_llava=true
```

**Aliases:** `/extract`, `/text`

**Options:**
- `languages` - Comma-separated language codes (default: en)
- `confidence` - Return confidence scores (default: false)
- `use_llava` - Force use of LLaVA instead of Tesseract (default: false)

**Language Codes:**
- `en` - English
- `es` - Spanish
- `fr` - French
- `de` - German
- `it` - Italian
- `pt` - Portuguese
- `ru` - Russian
- `ja` - Japanese
- `ko` - Korean
- `zh` - Chinese (Simplified)
- `ar` - Arabic

---

### `/vision-status` - Check Status

Check the status of vision plugins and capabilities.

**Syntax:**
```
/vision-status
```

**Aliases:** `/vstatus`, `/vision-info`

**Output:**
- List of available vision plugins
- Initialization status
- Plugin capabilities
- Version information
- Setup instructions (if plugins not initialized)

---

## 🎯 Use Cases

### 1. Code Screenshot Analysis

Analyze screenshots of code, error messages, or terminal output:

```bash
/image error_screenshot.png "What error is shown here and how do I fix it?"
/image terminal.png "Explain what commands were run"
```

### 2. Document Processing

Extract text from scanned documents, receipts, or invoices:

```bash
/ocr receipt.jpg
/ocr invoice.pdf confidence=true
/ocr multilingual_doc.png languages=en,es,fr
```

### 3. Diagram Understanding

Get explanations of diagrams, flowcharts, or system architecture:

```bash
/image architecture_diagram.png "Explain this system architecture"
/image flowchart.png "Walk me through this process step by step"
```

### 4. UI/UX Analysis

Analyze user interfaces, mockups, or design screenshots:

```bash
/image ui_mockup.png "Analyze the usability of this interface"
/image website.png "What improvements would you suggest for this design?"
```

### 5. Data Visualization Analysis

Understand charts, graphs, and data visualizations:

```bash
/image chart.png "What trends do you see in this data?"
/image graph.png "Summarize the key insights from this visualization"
```

### 6. Handwriting Recognition

Extract text from handwritten notes (works best with Tesseract + clear handwriting):

```bash
/ocr handwritten_note.jpg
/image note.png "What does this handwritten note say?"
```

---

## 🔧 Advanced Usage

### Programmatic Access (Python API)

```python
from gerdsenai_cli.plugins.registry import plugin_registry
from gerdsenai_cli.plugins.base import PluginCategory
from pathlib import Path

# Get LLaVA plugin
llava = plugin_registry.get(PluginCategory.VISION, "llava")

# Initialize
await llava.initialize()

# Analyze image
response = await llava.understand_image(
    image=Path("screenshot.png"),
    prompt="What's in this image?",
    temperature=0.7
)

print(response)

# Get Tesseract plugin
tesseract = plugin_registry.get(PluginCategory.VISION, "tesseract_ocr")

# Initialize
await tesseract.initialize()

# Extract text
text = await tesseract.ocr(
    image=Path("document.png"),
    languages=["en", "es"],
    return_confidence=True
)

print(f"Text: {text['text']}")
print(f"Confidence: {text['confidence']:.1f}%")
```

### Custom Model Configuration

Configure LLaVA with custom Ollama endpoint:

```python
from gerdsenai_cli.plugins.vision.llava_plugin import LLaVAPlugin

# Custom configuration
llava = LLaVAPlugin(
    ollama_url="http://192.168.1.100:11434",
    default_model="llava:13b",
    timeout=120.0
)

plugin_registry.register(llava)
await llava.initialize()
```

### Batch Processing

Process multiple images:

```python
import asyncio
from pathlib import Path

async def process_images(image_paths):
    llava = plugin_registry.get(PluginCategory.VISION, "llava")
    await llava.initialize()

    results = []
    for image_path in image_paths:
        response = await llava.understand_image(
            image=Path(image_path),
            prompt="Describe this image"
        )
        results.append({
            "image": image_path,
            "analysis": response
        })

    return results

# Process all PNGs in directory
images = list(Path("screenshots").glob("*.png"))
results = await process_images(images)
```

---

## 🎭 Model Comparison

### LLaVA Models

| Model | Size | VRAM | Speed | Quality | Use Case |
|-------|------|------|-------|---------|----------|
| llava:7b | 4.5GB | 6-8GB | Fast | Good | General purpose, daily use |
| llava:13b | 7.3GB | 12-16GB | Medium | Better | Detailed analysis, complex scenes |
| llava:34b | 19GB | 32GB+ | Slow | Best | Research, highest quality needs |
| bakllava | 4.5GB | 6-8GB | Fast | Good | Alternative with different training |

**Recommendation:** Start with `llava:7b` for the best balance of speed and quality.

### OCR Engines

| Engine | Accuracy | Speed | Languages | Use Case |
|--------|----------|-------|-----------|----------|
| Tesseract | High | Fast | 100+ | Documents, printed text |
| LLaVA | Medium | Slower | Any | Scene text, complex layouts |

**Recommendation:** Use Tesseract for documents, LLaVA for screenshots/UI.

---

## 🐛 Troubleshooting

### LLaVA Issues

**Problem:** "LLaVA plugin not available"

**Solutions:**
1. Check Ollama is running: `ollama list`
2. Pull LLaVA model: `ollama pull llava:7b`
3. Restart GerdsenAI CLI

---

**Problem:** "Request timed out"

**Solutions:**
1. Use smaller model: `model=llava:7b`
2. Increase timeout in plugin configuration
3. Reduce image size (resize to < 1920x1080)
4. Check system resources (CPU/GPU usage)

---

**Problem:** "Out of memory"

**Solutions:**
1. Switch to smaller model: `llava:7b` instead of `llava:13b`
2. Close other applications
3. Restart Ollama: `pkill ollama && ollama serve`

---

### Tesseract Issues

**Problem:** "Tesseract not found"

**Solutions:**
1. Install Tesseract: See installation instructions above
2. Verify installation: `tesseract --version`
3. Check PATH includes Tesseract binary

---

**Problem:** "Language not available"

**Solutions:**
1. List available languages: `tesseract --list-langs`
2. Install language pack: `sudo apt install tesseract-ocr-<lang>`
3. Use available language codes only

---

**Problem:** "Poor OCR accuracy"

**Solutions:**
1. Ensure image is high resolution (300 DPI+)
2. Image should have good contrast
3. Text should be horizontal (rotate if needed)
4. Try preprocessing: increase contrast, denoise
5. Use correct language codes: `languages=en,es`

---

## 🎯 Best Practices

### Image Analysis

1. **Use descriptive prompts:**
   - ❌ "What is this?"
   - ✅ "Describe the main objects and their arrangement in this image"

2. **Start with smaller models:**
   - Use `llava:7b` for general tasks
   - Only upgrade to `llava:13b` if quality insufficient

3. **Adjust temperature:**
   - `0.2-0.3` for factual analysis
   - `0.7-0.8` for creative descriptions
   - `0.9-1.0` for artistic interpretation

### OCR

1. **Preprocess images:**
   - Ensure good contrast
   - Remove noise/artifacts
   - Straighten text if skewed

2. **Specify languages:**
   - Always specify expected languages
   - Multi-language OCR works best with language hints

3. **Use appropriate engine:**
   - Tesseract for documents, forms, receipts
   - LLaVA for UI screenshots, embedded text

### Performance

1. **Lazy loading:**
   - Plugins initialize on first use
   - First command may be slower

2. **Caching:**
   - Ollama caches models in memory
   - Subsequent calls are faster

3. **Batch processing:**
   - Process multiple images in parallel
   - Use async programming for efficiency

---

## 🚀 Future Enhancements

### Planned Features

- **Audio Support:** Whisper integration for speech-to-text
- **Video Understanding:** Video analysis and frame extraction
- **Simulation Bridges:** Isaac Sim, Unreal Engine integration
- **Multi-Agent Orchestration:** Specialized vision agents
- **Tool Use Framework:** Vision tools for LLM agents
- **Streaming:** Real-time video/webcam analysis

---

## 📚 Examples

### Complete Workflow: Document Analysis

```bash
# 1. Check vision status
/vision-status

# 2. Extract text from document
/ocr scanned_document.png languages=en confidence=true

# 3. Analyze document layout
/image scanned_document.png "Describe the document structure and layout"

# 4. Ask specific questions
/image scanned_document.png "What is the main topic of this document?"
```

### Complete Workflow: Code Review from Screenshot

```bash
# 1. Analyze code screenshot
/image code_screenshot.png "Review this code for potential issues"

# 2. Extract code as text
/ocr code_screenshot.png

# 3. Get improvement suggestions
/image code_screenshot.png "What improvements would you suggest for this code?"
```

### Complete Workflow: UI Mockup Review

```bash
# 1. General analysis
/image ui_mockup.png "Describe the user interface and its components"

# 2. UX evaluation
/image ui_mockup.png "Evaluate the usability and user experience of this design"

# 3. Specific feedback
/image ui_mockup.png "What accessibility improvements would you suggest?"
```

---

## 🤝 Contributing

Want to add more vision capabilities? See:
- `gerdsenai_cli/plugins/base.py` - Plugin protocols
- `gerdsenai_cli/plugins/vision/` - Vision plugin implementations
- `docs/FRONTIER_ARCHITECTURE.md` - Complete architecture guide

---

## 📖 Additional Resources

- [Ollama Documentation](https://github.com/ollama/ollama)
- [LLaVA Paper](https://arxiv.org/abs/2304.08485)
- [Tesseract Documentation](https://github.com/tesseract-ocr/tesseract)
- [GerdsenAI Plugin System](./FRONTIER_ARCHITECTURE.md)

---

**Last Updated:** 2025-01-17
**Version:** 1.0.0 (Frontier AI - Phase 2)
