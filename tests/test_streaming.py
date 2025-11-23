#!/usr/bin/env python3
"""
Test streaming functionality of EnhancedConsole.

This script demonstrates the streaming response feature.
"""
import asyncio

from rich.console import Console

from gerdsenai_cli.ui.console import EnhancedConsole


async def simulate_streaming():
    """Simulate streaming response chunks."""
    response_text = """Here's a Python example:

```python
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

# Generate first 10 Fibonacci numbers
for i in range(10):
    print(f"F({i}) = {fibonacci(i)}")
```

This recursive implementation calculates Fibonacci numbers efficiently."""

    # Split into chunks for streaming simulation
    chunks = []
    chunk_size = 10
    for i in range(0, len(response_text), chunk_size):
        chunks.append(response_text[i:i+chunk_size])

    return chunks


async def test_tui_streaming():
    """Test TUI mode streaming."""
    print("\n" + "="*60)
    print("Testing TUI Mode Streaming")
    print("="*60 + "\n")

    console = Console()
    enhanced_console = EnhancedConsole(console)
    enhanced_console.set_tui_mode(True)

    # Update status bar
    enhanced_console.update_status(
        model="test-model",
        context_files=5,
        token_count=1500,
        current_task="Streaming demo"
    )

    # Start streaming
    user_input = "Show me a Fibonacci function"
    enhanced_console.start_streaming(user_input)

    # Simulate streaming chunks
    chunks = await simulate_streaming()
    accumulated = ""

    for chunk in chunks:
        accumulated += chunk
        enhanced_console.stream_chunk(chunk, accumulated)
        await asyncio.sleep(0.05)  # Simulate network delay

    enhanced_console.finish_streaming()

    print("\n✅ TUI streaming test complete!")


async def test_simple_streaming():
    """Test simple console mode streaming."""
    print("\n" + "="*60)
    print("Testing Simple Console Mode Streaming")
    print("="*60 + "\n")

    console = Console()
    enhanced_console = EnhancedConsole(console)
    enhanced_console.set_tui_mode(False)

    # Start streaming
    user_input = "Show me a Fibonacci function"
    enhanced_console.start_streaming(user_input)

    # Simulate streaming chunks
    chunks = await simulate_streaming()
    accumulated = ""

    for chunk in chunks:
        accumulated += chunk
        enhanced_console.stream_chunk(chunk, accumulated)
        await asyncio.sleep(0.05)  # Simulate network delay

    enhanced_console.finish_streaming()

    print("\n✅ Simple streaming test complete!")


async def main():
    """Run all streaming tests."""
    print("🚀 Enhanced Console Streaming Test")
    print("This demonstrates real-time streaming in both TUI and simple modes.")

    # Test TUI mode
    await test_tui_streaming()

    # Wait a bit
    await asyncio.sleep(2)

    # Test simple mode
    await test_simple_streaming()

    print("\n" + "="*60)
    print("All tests completed! 🎉")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
