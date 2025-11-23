"""
Test script for the enhanced TUI layout.

Run this to verify the new TUI components work correctly.
"""

import asyncio
from unittest.mock import Mock, patch

from rich.console import Console

from gerdsenai_cli.ui.console import EnhancedConsole


async def test_tui():
    """Test the enhanced TUI."""
    console = Console()
    enhanced = EnhancedConsole(console)

    # Update status
    enhanced.update_status(
        model="mistralai/magistral-small-2509",
        context_files=52,
        token_count=1234
    )

    # Test simple message
    print("\n=== Test 1: Simple message ===")
    enhanced.print_message(
        user_input="Hello, can you help me?",
        ai_response="Of course! I'm here to help you with your coding tasks. What would you like to work on?"
    )

    await asyncio.sleep(0.1)  # Shorter sleep for tests

    # Test message with code
    print("\n=== Test 2: Message with code ===")
    code_response = """Sure! Here's a Python function that calculates fibonacci numbers:

```python
def fibonacci(n: int) -> int:
    \"\"\"Calculate the nth Fibonacci number.\"\"\"
    if n <= 1:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)

# Example usage
print(fibonacci(10))
```

This is a recursive implementation. For better performance with large numbers, consider using dynamic programming or memoization."""

    enhanced.print_message(
        user_input="Write a fibonacci function in Python",
        ai_response=code_response
    )

    await asyncio.sleep(0.1)  # Shorter sleep for tests

    # Test confirmation - mock the input to avoid stdin issues in pytest
    print("\n=== Test 3: Confirmation prompt ===")
    with patch('rich.prompt.Confirm.ask', return_value=True):
        result = enhanced.confirm("Would you like to apply these changes?", default=True)
        print(f"User confirmed: {result}")

    # Test various messages
    print("\n=== Test 4: Status messages ===")
    enhanced.print_info("This is an info message")
    enhanced.print_success("Operation completed successfully!")
    enhanced.print_warning("This is a warning")
    enhanced.print_error("This is an error message")


if __name__ == "__main__":
    asyncio.run(test_tui())
