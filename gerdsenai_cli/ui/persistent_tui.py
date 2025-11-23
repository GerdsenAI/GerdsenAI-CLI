"""
Persistent TUI mode - always-on display with conversation history and input field.

Similar to Claude CLI and Gemini CLI where the layout is always visible with:
- Header at top
- Scrollable conversation history in middle
- Fixed input field at bottom
"""

from datetime import datetime

from prompt_toolkit import PromptSession
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.patch_stdout import patch_stdout
from rich.console import Console, Group, RenderableType
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.text import Text


class ConversationMessage:
    """Represents a single message in the conversation."""

    def __init__(self, role: str, content: str, timestamp: datetime | None = None):
        """Initialize a conversation message.

        Args:
            role: "user" or "assistant"
            content: Message content
            timestamp: When the message was created
        """
        self.role = role
        self.content = content
        self.timestamp = timestamp or datetime.now()


class PersistentTUI:
    """Persistent TUI that stays visible during entire session.

    Provides a chat-like interface similar to Claude CLI and Gemini CLI where:
    - The layout is always visible
    - User types at the bottom
    - Conversation scrolls in the middle
    - Responses stream in real-time
    """

    def __init__(self, console: Console):
        """Initialize the persistent TUI.

        Args:
            console: Rich console instance
        """
        self.console = console
        self.messages: list[ConversationMessage] = []
        self.layout = Layout()
        self.live: Live | None = None
        self.streaming_content = ""
        self.prompt_session: PromptSession | None = None
        self.status_text = "Type your message and press Enter"

        # Setup layout structure
        self._setup_layout()

    def _setup_layout(self) -> None:
        """Setup the persistent layout structure."""
        self.layout.split(
            Layout(name="header", size=3),
            Layout(name="conversation", ratio=1),
            Layout(
                name="input_area", size=5
            ),  # Fixed input at bottom with room for border
        )

        # Initial render
        self._update_layout()

    def _render_header(self) -> Panel:
        """Render the header panel.

        Returns:
            Header panel with title and branding
        """
        return Panel(
            Text(
                "🤖 GerdsenAI CLI - Interactive Chat Mode",
                justify="center",
                style="bold cyan",
            ),
            style="cyan",
            border_style="bright_cyan",
        )

    def _render_conversation(self) -> RenderableType:
        """Render the conversation history.

        Returns:
            Group of panels representing the conversation
        """
        if not self.messages and not self.streaming_content:
            return Panel(
                Text(
                    "No messages yet.\n\nType your message at the prompt below and press Enter to start.",
                    justify="center",
                    style="dim italic",
                ),
                border_style="dim",
            )

        panels = []

        # Render all completed messages
        for msg in self.messages:
            timestamp = msg.timestamp.strftime("%H:%M:%S")

            if msg.role == "user":
                panel = Panel(
                    Text(msg.content, style="white"),
                    title=f"[bold blue]You[/bold blue] · {timestamp}",
                    title_align="left",
                    border_style="blue",
                    padding=(1, 2),
                )
            else:
                panel = Panel(
                    Text(msg.content, style="white"),
                    title=f"[bold green]GerdsenAI[/bold green] · {timestamp}",
                    title_align="left",
                    border_style="green",
                    padding=(1, 2),
                )
            panels.append(panel)

        # Add streaming content if present
        if self.streaming_content:
            streaming_panel = Panel(
                Text(self.streaming_content + "▌", style="white"),  # Add cursor
                title="[bold yellow]GerdsenAI[/bold yellow] · streaming...",
                title_align="left",
                border_style="yellow",
                padding=(1, 2),
            )
            panels.append(streaming_panel)

        return Group(*panels)

    def _render_input_area(self) -> Panel:
        """Render the fixed input area at bottom.

        Returns:
            Input area panel with prompt and status
        """
        status_parts = [
            f"� {len(self.messages)} messages",
            f"📝 {self.status_text}",
            "⌃C to exit",
        ]

        content = Text()
        content.append("⬇️  ", style="bold yellow")
        content.append(
            "Type your message at the prompt below this panel", style="italic yellow"
        )
        content.append(" ⬇️\n\n", style="bold yellow")
        content.append(" │ ".join(status_parts), style="dim")

        return Panel(
            content,
            title="[bold yellow]⚠️  Input appears below this panel[/bold yellow]",
            title_align="left",
            border_style="yellow",
            padding=(0, 2),
        )

    def _update_layout(self) -> None:
        """Update the layout with current content."""
        self.layout["header"].update(self._render_header())
        self.layout["conversation"].update(self._render_conversation())
        self.layout["input_area"].update(self._render_input_area())

    def start(self) -> None:
        """Start the persistent TUI with Live display."""
        self._update_layout()
        self.live = Live(
            self.layout,
            console=self.console,
            screen=False,  # Don't use alternate screen to preserve scrollback
            refresh_per_second=10,
            transient=False,
        )
        self.live.start()

        # Initialize prompt session
        self.prompt_session = PromptSession()

    def stop(self) -> None:
        """Stop the Live display."""
        if self.live:
            self.live.stop()
            self.live = None

    def add_user_message(self, content: str) -> None:
        """Add a user message to conversation.

        Args:
            content: User's message content
        """
        msg = ConversationMessage("user", content)
        self.messages.append(msg)
        self._update_layout()
        if self.live:
            self.live.refresh()

    def start_assistant_message(self) -> None:
        """Start streaming an assistant message."""
        self.streaming_content = ""
        self.status_text = "🤖 GerdsenAI is thinking..."
        self._update_layout()
        if self.live:
            self.live.refresh()

    def append_streaming_content(self, content: str) -> None:
        """Append content to the streaming assistant message.

        Args:
            content: Content chunk to append
        """
        self.streaming_content += content
        self.status_text = "🤖 GerdsenAI is responding..."
        self._update_layout()
        if self.live:
            self.live.refresh()

    def finish_assistant_message(self) -> None:
        """Finish the streaming assistant message."""
        if self.streaming_content:
            msg = ConversationMessage("assistant", self.streaming_content)
            self.messages.append(msg)
            self.streaming_content = ""

        self.status_text = "Type your message and press Enter"
        self._update_layout()
        if self.live:
            self.live.refresh()

    def set_status(self, status: str) -> None:
        """Set the status bar text.

        Args:
            status: Status message to display
        """
        self.status_text = status
        self._update_layout()
        if self.live:
            self.live.refresh()

    async def get_user_input(self) -> str:
        """Get user input from bottom prompt while keeping TUI visible.

        Returns:
            User's input string
        """
        if not self.prompt_session:
            self.prompt_session = PromptSession()

        # NOTE: Input happens BELOW the TUI panel, not inside it
        # This is a limitation of using Rich Live display with prompt_toolkit
        # To fix this properly would require rebuilding with prompt_toolkit Application framework

        # Temporarily stop Live to allow input
        live_was_active = self.live is not None
        if live_was_active and self.live:
            self.live.stop()

        try:
            # Use patch_stdout to prevent prompt from interfering with display
            with patch_stdout():
                # Show a clear, prominent input prompt
                user_input = await self.prompt_session.prompt_async(
                    HTML(
                        '\n<style fg="#00FFFF" bold="true">━━━ Type your message below (press Enter to send) ━━━</style>\n'
                        '<style fg="#00FFFF" bold="true">GerdsenAI</style><prompt> > </prompt>'
                    ),
                    multiline=False,
                )

            # Restart Live display
            if live_was_active:
                self.live = Live(
                    self.layout,
                    console=self.console,
                    screen=False,
                    refresh_per_second=10,
                    transient=False,
                )
                self.live.start()

            return user_input.strip()

        except (EOFError, KeyboardInterrupt):
            # Restart Live before raising
            if live_was_active and not self.live:
                self.live = Live(
                    self.layout,
                    console=self.console,
                    screen=False,
                    refresh_per_second=10,
                    transient=False,
                )
                self.live.start()
            raise
