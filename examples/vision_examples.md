# Vision Examples - Quick Reference

## 🎨 Image Understanding Examples

### Basic Image Analysis
```bash
# Describe an image
/image photo.jpg

# Analyze a screenshot
/image screenshot.png "What's happening in this screenshot?"

# Understand a diagram
/image diagram.png "Explain this diagram step by step"
```

### Code Analysis
```bash
# Review code from screenshot
/image code.png "Review this code for potential bugs"

# Explain error messages
/image error.png "What error is shown and how do I fix it?"

# Analyze terminal output
/image terminal.png "Explain what these commands do"
```

### UI/UX Analysis
```bash
# Evaluate interface
/image ui_mockup.png "Evaluate the usability of this interface"

# Compare designs
/image design_v1.png "What are the strengths and weaknesses of this design?"

# Accessibility review
/image app_screenshot.png "What accessibility improvements would you suggest?"
```

### Data Visualization
```bash
# Analyze charts
/image chart.png "What trends do you see in this data?"

# Summarize graphs
/image graph.png "Summarize the key insights from this visualization"

# Compare data
/image comparison_chart.png "Compare the performance across categories"
```

### Creative Content
```bash
# Artistic analysis
/image artwork.png "Describe the artistic style and techniques" temperature=0.9

# Scene description
/image landscape.png "Describe this scene in vivid detail"

# Object identification
/image objects.jpg "List all the objects you can identify"
```

---

## 📝 OCR Examples

### Basic Text Extraction
```bash
# Extract text from image
/ocr document.png

# Scanned page
/ocr scanned_page.jpg

# Receipt processing
/ocr receipt.jpg
```

### Multi-Language OCR
```bash
# English + Spanish
/ocr bilingual_doc.png languages=en,es

# French document
/ocr french_doc.jpg languages=fr

# Asian languages
/ocr chinese_doc.png languages=zh
```

### Advanced OCR
```bash
# With confidence scores
/ocr difficult_image.png confidence=true

# Force LLaVA OCR
/ocr screenshot_text.png use_llava=true

# Multiple languages with confidence
/ocr complex_doc.png languages=en,es,fr confidence=true
```

---

## 🔬 Advanced Workflows

### Document Processing Pipeline
```bash
# 1. Check status
/vision-status

# 2. Extract all text
/ocr document.pdf confidence=true

# 3. Analyze document structure
/image document.pdf "Describe the document layout and sections"

# 4. Get summary
/image document.pdf "Summarize the key points from this document"
```

### Code Review from Screenshot
```bash
# 1. Get code overview
/image code.png "What does this code do?"

# 2. Security analysis
/image code.png "Are there any security vulnerabilities?"

# 3. Extract code as text
/ocr code.png

# 4. Improvement suggestions
/image code.png "How could this code be improved?"
```

### UI Mockup Review
```bash
# 1. General description
/image mockup.png "Describe the layout and components"

# 2. UX evaluation
/image mockup.png "Evaluate the user experience"

# 3. Accessibility check
/image mockup.png "Check for accessibility issues"

# 4. Improvement suggestions
/image mockup.png "What improvements would you suggest?"
```

### Error Debugging
```bash
# 1. Understand the error
/image error_screenshot.png "What error occurred?"

# 2. Get context
/image error_screenshot.png "What was the user trying to do?"

# 3. Solution suggestions
/image error_screenshot.png "How do I fix this error?"

# 4. Extract error text
/ocr error_screenshot.png
```

---

## 🎯 Model Selection Guide

### When to use llava:7b (default)
- General image analysis
- Quick descriptions
- Daily usage
- Resource-constrained systems

```bash
/image photo.jpg  # Uses llava:7b by default
```

### When to use llava:13b
- Detailed analysis needed
- Complex scenes
- Technical diagrams
- Higher accuracy requirements

```bash
/image complex_diagram.png model=llava:13b
```

### When to use llava:34b
- Research purposes
- Highest quality needed
- Complex reasoning required
- Multiple objects/relationships

```bash
/image research_image.png model=llava:34b
```

---

## 🌡️ Temperature Guide

### Low Temperature (0.2-0.3)
For factual, deterministic analysis:
```bash
/image document.png "Extract the key facts" temperature=0.2
```

### Medium Temperature (0.7-0.8)
Balanced creativity and accuracy:
```bash
/image scene.jpg  # Default 0.7
```

### High Temperature (0.9-1.0)
For creative, varied responses:
```bash
/image artwork.png "Describe the artistic style" temperature=0.9
```

---

## 🌐 Language Codes Reference

### Common Languages
```bash
en  # English
es  # Spanish
fr  # French
de  # German
it  # Italian
pt  # Portuguese
ru  # Russian
ja  # Japanese
ko  # Korean
zh  # Chinese
ar  # Arabic
hi  # Hindi
```

### Multi-Language Examples
```bash
# English + Spanish receipt
/ocr receipt.jpg languages=en,es

# French + German document
/ocr document.png languages=fr,de

# Asian languages
/ocr asian_doc.png languages=ja,ko,zh
```

---

## 💡 Pro Tips

### Image Analysis Tips
1. **Be specific in prompts**: "Identify all UI elements" > "What's this?"
2. **Use follow-up questions**: Analyze once, ask multiple questions
3. **Adjust temperature**: Lower for facts, higher for creativity
4. **Choose right model**: Start with 7b, upgrade if needed

### OCR Tips
1. **Specify languages**: Always provide language hints
2. **Preprocess images**: Increase contrast, straighten text
3. **Use Tesseract for documents**: More accurate than LLaVA
4. **Use LLaVA for screenshots**: Better for embedded text in UI

### Performance Tips
1. **First use is slower**: Plugins initialize on first command
2. **Batch similar tasks**: Multiple images analyzed faster together
3. **Resize large images**: < 1920x1080 for better speed
4. **Keep Ollama running**: Faster subsequent requests

---

## 🐛 Common Issues

### "LLaVA plugin not available"
```bash
# Fix:
ollama pull llava:7b
# Restart GerdsenAI CLI
```

### "Tesseract not found"
```bash
# Ubuntu/Debian:
sudo apt install tesseract-ocr

# macOS:
brew install tesseract

# Python packages:
pip install pytesseract pillow
```

### "Request timed out"
```bash
# Use smaller model:
/image large_file.jpg model=llava:7b

# Or resize image first
```

### "Poor OCR quality"
```bash
# Ensure high resolution (300+ DPI)
# Use correct language codes
# Preprocess: increase contrast, denoise
```

---

## 📚 More Examples

See full documentation:
- `docs/VISION_INTEGRATION.md` - Complete guide
- `docs/FRONTIER_ARCHITECTURE.md` - Plugin system architecture

---

**Quick Command Reference:**

```bash
/image <path> [prompt]              # Analyze image
/ocr <path> [languages=en,es]       # Extract text
/vision-status                      # Check status

# Aliases
/img, /vision                       # Same as /image
/extract, /text                     # Same as /ocr
/vstatus                            # Same as /vision-status
```
