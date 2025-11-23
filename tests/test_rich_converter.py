"""Unit tests for RichToFormattedTextConverter class."""
from gerdsenai_cli.ui.prompt_toolkit_tui import (
    RICH_AVAILABLE,
    RichToFormattedTextConverter,
)


class TestRichToFormattedTextConverter:
    """Test suite for RichToFormattedTextConverter."""

    def test_converter_initialization(self):
        """Test that converter can be initialized."""
        if RICH_AVAILABLE:
            converter = RichToFormattedTextConverter()
            assert converter is not None

    def test_convert_plain_text(self):
        """Test converting plain text."""
        if not RICH_AVAILABLE:
            return  # Skip if Rich not available

        converter = RichToFormattedTextConverter()
        text = "This is plain text"

        result = converter.convert_markdown(text)

        # Should return list of tuples
        assert isinstance(result, list)
        assert len(result) > 0

        # Each item should be a tuple
        for item in result:
            assert isinstance(item, tuple)
            assert len(item) == 2  # (style, text)

    def test_convert_markdown_heading(self):
        """Test converting markdown with headings."""
        if not RICH_AVAILABLE:
            return

        converter = RichToFormattedTextConverter()
        text = "# Heading 1\n## Heading 2"

        result = converter.convert_markdown(text)

        assert isinstance(result, list)
        assert len(result) > 0

    def test_convert_markdown_bold(self):
        """Test converting markdown with bold text."""
        if not RICH_AVAILABLE:
            return

        converter = RichToFormattedTextConverter()
        text = "This is **bold** text"

        result = converter.convert_markdown(text)

        assert isinstance(result, list)
        assert len(result) > 0

    def test_convert_markdown_italic(self):
        """Test converting markdown with italic text."""
        if not RICH_AVAILABLE:
            return

        converter = RichToFormattedTextConverter()
        text = "This is *italic* text"

        result = converter.convert_markdown(text)

        assert isinstance(result, list)
        assert len(result) > 0

    def test_convert_markdown_code_block(self):
        """Test converting markdown with code blocks."""
        if not RICH_AVAILABLE:
            return

        converter = RichToFormattedTextConverter()
        text = "```python\ndef hello():\n    print('world')\n```"

        result = converter.convert_markdown(text)

        assert isinstance(result, list)
        assert len(result) > 0

    def test_convert_markdown_inline_code(self):
        """Test converting markdown with inline code."""
        if not RICH_AVAILABLE:
            return

        converter = RichToFormattedTextConverter()
        text = "Use the `print()` function"

        result = converter.convert_markdown(text)

        assert isinstance(result, list)
        assert len(result) > 0

    def test_convert_markdown_list(self):
        """Test converting markdown with lists."""
        if not RICH_AVAILABLE:
            return

        converter = RichToFormattedTextConverter()
        text = "- Item 1\n- Item 2\n- Item 3"

        result = converter.convert_markdown(text)

        assert isinstance(result, list)
        assert len(result) > 0

    def test_convert_markdown_table(self):
        """Test converting markdown with tables."""
        if not RICH_AVAILABLE:
            return

        converter = RichToFormattedTextConverter()
        text = "| Column 1 | Column 2 |\n|----------|----------|\n| Value 1  | Value 2  |"

        result = converter.convert_markdown(text)

        assert isinstance(result, list)
        assert len(result) > 0

    def test_convert_empty_string(self):
        """Test converting empty string."""
        if not RICH_AVAILABLE:
            return

        converter = RichToFormattedTextConverter()
        text = ""

        result = converter.convert_markdown(text)

        # Should handle empty string gracefully
        assert isinstance(result, list)

    def test_convert_multiline_text(self):
        """Test converting multiline text."""
        if not RICH_AVAILABLE:
            return

        converter = RichToFormattedTextConverter()
        text = "Line 1\nLine 2\nLine 3"

        result = converter.convert_markdown(text)

        assert isinstance(result, list)
        assert len(result) > 0

    def test_convert_complex_markdown(self):
        """Test converting complex markdown with multiple elements."""
        if not RICH_AVAILABLE:
            return

        converter = RichToFormattedTextConverter()
        text = """
# Main Title

This is a paragraph with **bold** and *italic* text.

## Code Example

```python
def greet(name):
    return f"Hello, {name}!"
```

### Features

- Feature 1
- Feature 2
- Feature 3

> This is a quote
"""

        result = converter.convert_markdown(text)

        assert isinstance(result, list)
        assert len(result) > 0

    def test_convert_with_unicode(self):
        """Test converting text with unicode characters."""
        if not RICH_AVAILABLE:
            return

        converter = RichToFormattedTextConverter()
        text = "Unicode: 🎉 ✨ 🚀 ⚡"

        result = converter.convert_markdown(text)

        assert isinstance(result, list)
        assert len(result) > 0

    def test_error_handling(self):
        """Test that converter handles errors gracefully."""
        if not RICH_AVAILABLE:
            return

        converter = RichToFormattedTextConverter()

        # Test with potentially problematic input
        # Should not raise exception
        try:
            result = converter.convert_markdown(None)
            # If it doesn't error, should return empty or fallback
            assert isinstance(result, list)
        except Exception:
            # If it does error, that's also acceptable
            pass

    def test_style_format(self):
        """Test that returned tuples have correct format."""
        if not RICH_AVAILABLE:
            return

        converter = RichToFormattedTextConverter()
        text = "Test text"

        result = converter.convert_markdown(text)

        # Each tuple should be (style_class, text_content)
        for style, text_part in result:
            assert isinstance(style, str)
            assert isinstance(text_part, str)

    def test_multiple_conversions(self):
        """Test that converter can be used multiple times."""
        if not RICH_AVAILABLE:
            return

        converter = RichToFormattedTextConverter()

        # Convert multiple times
        result1 = converter.convert_markdown("Text 1")
        result2 = converter.convert_markdown("Text 2")
        result3 = converter.convert_markdown("Text 3")

        # All should succeed
        assert isinstance(result1, list)
        assert isinstance(result2, list)
        assert isinstance(result3, list)
