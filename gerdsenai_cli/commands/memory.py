"""
Memory management commands for GerdsenAI CLI.

Provides slash commands for inspecting and managing the persistent
project memory system.
"""

import logging
from typing import TYPE_CHECKING

from rich.console import Console
from rich.table import Table

from .base import BaseCommand, CommandCategory

if TYPE_CHECKING:
    from ..core.agent import Agent

logger = logging.getLogger(__name__)
console = Console()


class MemoryCommand(BaseCommand):
    """Command for managing project memory."""
    
    def __init__(self, agent: "Agent | None" = None):
        self.agent = agent
    
    @property
    def name(self) -> str:
        return "memory"
    
    @property
    def description(self) -> str:
        return "Manage project memory (files, topics, preferences)"
    
    @property
    def usage(self) -> str:
        return """Usage: /memory <subcommand> [args]

Subcommands:
  show [files|topics|preferences]  Show memory contents
  stats                           Show memory statistics
  recall <file|topic> <name>      Recall information about a file or topic
  forget <file|topic> <name>      Forget a file or topic
  clear                           Clear all memory (requires confirmation)
  save                            Manually save memory to disk
  
Examples:
  /memory show files
  /memory stats
  /memory recall file src/main.py
  /memory forget topic testing
  /memory clear
"""
    
    @property
    def category(self) -> CommandCategory:
        return CommandCategory.SYSTEM
    
    async def execute(self, args: str) -> str:
        """Execute memory command.
        
        Args:
            args: Command arguments
            
        Returns:
            Command result message
        """
        if not self.agent or not self.agent.memory:
            return "❌ Memory system not available"
        
        parts = args.strip().split(maxsplit=1)
        if not parts:
            return self.usage
        
        subcommand = parts[0].lower()
        subargs = parts[1] if len(parts) > 1 else ""
        
        if subcommand == "show":
            return await self._show_memory(subargs)
        elif subcommand == "stats":
            return await self._show_stats()
        elif subcommand == "recall":
            return await self._recall(subargs)
        elif subcommand == "forget":
            return await self._forget(subargs)
        elif subcommand == "clear":
            return await self._clear_memory()
        elif subcommand == "save":
            return await self._save_memory()
        else:
            return f"Unknown subcommand: {subcommand}\n\n{self.usage}"
    
    async def _show_memory(self, args: str) -> str:
        """Show memory contents."""
        if not self.agent or not self.agent.memory:
            return "❌ Memory system not available"
        
        memory = self.agent.memory
        
        # Parse what to show
        show_type = args.strip().lower() or "all"
        
        if show_type in ["files", "all"]:
            console.print("\n[bold cyan]📁 Remembered Files[/bold cyan]")
            
            if not memory.files:
                console.print("  [dim]No files in memory yet[/dim]")
            else:
                table = Table(show_header=True, header_style="bold magenta")
                table.add_column("Path", style="cyan")
                table.add_column("Mentions", justify="right", style="yellow")
                table.add_column("Last Mentioned", style="green")
                table.add_column("Topics", style="blue")
                
                for file_ref in memory.get_recent_files(20):
                    table.add_row(
                        file_ref.path,
                        str(file_ref.mention_count),
                        file_ref.last_mentioned[:10],  # Just the date
                        ", ".join(file_ref.topics[:3]) or "-"
                    )
                
                console.print(table)
        
        if show_type in ["topics", "all"]:
            console.print("\n[bold cyan]💭 Remembered Topics[/bold cyan]")
            
            if not memory.topics:
                console.print("  [dim]No topics in memory yet[/dim]")
            else:
                table = Table(show_header=True, header_style="bold magenta")
                table.add_column("Topic", style="cyan")
                table.add_column("Mentions", justify="right", style="yellow")
                table.add_column("Last Mentioned", style="green")
                table.add_column("Related Files", justify="right", style="blue")
                
                for topic_name, topic_ref in list(memory.topics.items())[:20]:
                    table.add_row(
                        topic_name,
                        str(topic_ref.mention_count),
                        topic_ref.last_mentioned[:10],
                        str(len(topic_ref.related_files))
                    )
                
                console.print(table)
        
        if show_type in ["preferences", "all"]:
            console.print("\n[bold cyan]⚙️  Learned Preferences[/bold cyan]")
            
            if not memory.preferences:
                console.print("  [dim]No preferences learned yet[/dim]")
            else:
                table = Table(show_header=True, header_style="bold magenta")
                table.add_column("Key", style="cyan")
                table.add_column("Value", style="yellow")
                table.add_column("Confidence", justify="right", style="green")
                table.add_column("Source", style="blue")
                
                for pref_key, pref in list(memory.preferences.items())[:20]:
                    table.add_row(
                        pref_key,
                        str(pref.value)[:50],  # Truncate long values
                        f"{pref.confidence:.1%}",
                        pref.learned_from
                    )
                
                console.print(table)
        
        return ""
    
    async def _show_stats(self) -> str:
        """Show memory statistics."""
        if not self.agent or not self.agent.memory:
            return "❌ Memory system not available"
        
        memory = self.agent.memory
        
        console.print("\n[bold cyan]📊 Memory Statistics[/bold cyan]\n")
        
        stats = [
            ("Files tracked", len(memory.files)),
            ("Topics tracked", len(memory.topics)),
            ("Preferences learned", len(memory.preferences)),
            ("Total sessions", memory.metadata.get("session_count", 0)),
            ("Created", memory.metadata.get("created_at", "N/A")),
            ("Last updated", memory.metadata.get("last_updated", "N/A")),
        ]
        
        table = Table(show_header=False, box=None)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="yellow")
        
        for metric, value in stats:
            # Format dates nicely
            if isinstance(value, str) and "T" in value:
                value = value[:10]  # Just the date
            table.add_row(f"  {metric}:", str(value))
        
        console.print(table)
        
        # Show memory file path
        console.print(f"\n[dim]Memory stored in: {memory.memory_file}[/dim]")
        
        return ""
    
    async def _recall(self, args: str) -> str:
        """Recall information about a file or topic."""
        if not self.agent or not self.agent.memory:
            return "❌ Memory system not available"
        
        memory = self.agent.memory
        
        parts = args.strip().split(maxsplit=1)
        if len(parts) != 2:
            return "Usage: /memory recall <file|topic> <name>"
        
        recall_type, name = parts
        
        if recall_type == "file":
            ref = memory.recall_file(name)
            if not ref:
                return f"❌ No memory of file: {name}"
            
            console.print(f"\n[bold cyan]📁 File: {ref.path}[/bold cyan]")
            console.print(f"  First mentioned: {ref.first_mentioned[:10]}")
            console.print(f"  Last mentioned: {ref.last_mentioned[:10]}")
            console.print(f"  Mention count: {ref.mention_count}")
            if ref.topics:
                console.print(f"  Topics: {', '.join(ref.topics)}")
            
        elif recall_type == "topic":
            ref = memory.recall_topic(name)
            if not ref:
                return f"❌ No memory of topic: {name}"
            
            console.print(f"\n[bold cyan]💭 Topic: {ref.name}[/bold cyan]")
            console.print(f"  First mentioned: {ref.first_mentioned[:10]}")
            console.print(f"  Last mentioned: {ref.last_mentioned[:10]}")
            console.print(f"  Mention count: {ref.mention_count}")
            if ref.related_files:
                console.print(f"  Related files ({len(ref.related_files)}):")
                for file_path in ref.related_files[:10]:
                    console.print(f"    • {file_path}")
            if ref.keywords:
                console.print(f"  Keywords: {', '.join(ref.keywords)}")
        else:
            return f"Unknown recall type: {recall_type}"
        
        return ""
    
    async def _forget(self, args: str) -> str:
        """Forget a file or topic from memory."""
        if not self.agent or not self.agent.memory:
            return "❌ Memory system not available"
        
        memory = self.agent.memory
        
        parts = args.strip().split(maxsplit=1)
        if len(parts) != 2:
            return "Usage: /memory forget <file|topic> <name>"
        
        forget_type, name = parts
        
        if forget_type == "file":
            if memory.forget_file(name):
                memory.save()
                return f"✅ Forgot file: {name}"
            else:
                return f"❌ No memory of file: {name}"
        
        elif forget_type == "topic":
            if memory.forget_topic(name):
                memory.save()
                return f"✅ Forgot topic: {name}"
            else:
                return f"❌ No memory of topic: {name}"
        
        else:
            return f"Unknown forget type: {forget_type}"
    
    async def _clear_memory(self) -> str:
        """Clear all memory (requires confirmation)."""
        if not self.agent or not self.agent.memory:
            return "❌ Memory system not available"
        
        memory = self.agent.memory
        
        console.print("\n[bold red]⚠️  Warning: This will clear ALL memory![/bold red]")
        console.print(f"  • {len(memory.files)} files")
        console.print(f"  • {len(memory.topics)} topics")
        console.print(f"  • {len(memory.preferences)} preferences")
        console.print("\nType 'yes' to confirm: ", end="")
        
        # Note: In real implementation, this would need proper input handling
        # For now, we return a message asking the user to confirm
        return "\n❌ Clear cancelled. Use `/memory clear --confirm` to force."
    
    async def _save_memory(self) -> str:
        """Manually save memory to disk."""
        if not self.agent or not self.agent.memory:
            return "❌ Memory system not available"
        
        memory = self.agent.memory
        
        if memory.save():
            return f"✅ Memory saved to {memory.memory_file}"
        else:
            return "❌ Failed to save memory"
