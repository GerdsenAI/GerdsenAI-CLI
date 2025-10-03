#!/usr/bin/env python3
"""
Demo script to test the enhanced TUI layout.
"""

import time

from rich.console import Console

from gerdsenai_cli.ui.console import EnhancedConsole


def main():
    """Run TUI demo."""
    console = Console()
    enhanced_console = EnhancedConsole(console)
    
    console.clear()
    console.print("[bold cyan]GerdsenAI TUI Demo[/bold cyan]\n")
    
    # Update status bar
    enhanced_console.update_status(
        model="mistralai/magistral-small-2509",
        context_files=52,
        token_count=9600,
        current_task="Sublimating..."
    )
    
    # Show a sample conversation
    user_input = "Explain how the agent system works"
    
    ai_response = """The agent system in GerdsenAI CLI works through several components:

1. **Intent Detection**: The system uses LLM-based intent parsing to understand what the user wants to do.

2. **Command Routing**: Based on the detected intent, the appropriate command handler is invoked.

3. **Context Management**: The agent maintains context about the project files and conversation history.

Here's a code example:

```python
class Agent:
    async def process_user_input(self, user_input: str):
        # Detect intent
        intent = await self.intent_parser.detect_intent(user_input)
        
        # Route to handler
        result = await self.execute_action(intent)
        
        return result
```

The system is fully async and uses httpx for LLM communication."""
    
    # Display the conversation
    enhanced_console.print_message(
        user_input=user_input,
        ai_response=ai_response
    )
    
    console.print("\n[dim]Press Ctrl+C to exit[/dim]")
    
    try:
        # Keep the display visible
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        console.print("\n[cyan]Demo ended.[/cyan]")


if __name__ == "__main__":
    main()
