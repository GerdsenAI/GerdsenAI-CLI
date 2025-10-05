"""
prompt_toolkit-based TUI with true embedded input.

Enhanced with:
    COMMANDS = {
        '/help': 'Show available commands',
        '/clear': 'Clear conversation history',
        '/model': 'Show or switch AI model (usage: /model [name])',
        '/mode': 'Show or switch execution mode (usage: /mode [architect|execute])',
        '/debug': 'Toggle debug mode',
        '/save': 'Save conversation to file',
        '/load': 'Load conversation from file',
        '/export': 'Export conversation to markdown',
        '/shortcuts': 'Show keyboard shortcuts',
        '/exit': 'Exit the application',
        '/quit': 'Exit the application',
    }d system (/help, /clear, /model, etc.)
- Rich markdown rendering for AI responses
- Comprehensive logging for debugging

Key features:
- Embedded input (type directly in the TUI)
- Real-time streaming updates
- Claude CLI-style sticky-bottom auto-scroll
- Native keyboard handling
- Scrollable conversation with proper scrollbar
- No display interruption during input
"""

import asyncio
import logging
from collections.abc import Awaitable
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional, cast

from prompt_toolkit import Application
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.document import Document
from prompt_toolkit.formatted_text import FormattedText, fragment_list_to_text, to_formatted_text
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout.containers import (
    HSplit,
    ScrollOffsets,
    Window,
)
from prompt_toolkit.layout.controls import BufferControl, FormattedTextControl
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.layout.margins import ScrollbarMargin
from prompt_toolkit.layout.processors import (
    HighlightSelectionProcessor,
    Processor,
    Transformation,
)
from prompt_toolkit.styles import Style
from prompt_toolkit.widgets import Frame

try:
    from rich.console import Console
    from rich.markdown import Markdown
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

from ..core.modes import ExecutionMode, ModeManager

# Set up logging
log_dir = Path.home() / ".gerdsenai" / "logs"
log_dir.mkdir(parents=True, exist_ok=True)
log_file = log_dir / "tui.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
    ]
)
logger = logging.getLogger(__name__)
logger.info(f"TUI logging initialized - log file: {log_file}")


class CommandParser:
    """Parse and handle TUI commands."""
    
    COMMANDS = {
        '/help': 'Show available commands',
        '/clear': 'Clear conversation history',
        '/model': 'Show or switch AI model (usage: /model [name])',
        '/debug': 'Toggle debug mode',
        '/save': 'Save conversation to file',
        '/load': 'Load conversation from file',
        '/export': 'Export conversation to markdown',
        '/shortcuts': 'Show keyboard shortcuts',
        '/exit': 'Exit the application',
        '/quit': 'Exit the application',
    }
    
    @staticmethod
    def is_command(text: str) -> bool:
        """Check if text is a command."""
        return text.strip().startswith('/')
    
    @staticmethod
    def parse(text: str) -> tuple[str, list[str]]:
        """Parse command and arguments.
        
        Returns:
            (command, args) tuple
        """
        parts = text.strip().split()
        command = parts[0] if parts else ''
        args = parts[1:] if len(parts) > 1 else []
        return command, args
    
    @staticmethod
    def get_help_text() -> str:
        """Generate formatted help text for all commands."""
        lines = ["Available Commands:", ""]
        for cmd, desc in CommandParser.COMMANDS.items():
            lines.append(f"  {cmd:<15} - {desc}")
        return "\n".join(lines)

    @staticmethod
    def get_shortcuts_text() -> str:
        """Generate formatted keyboard shortcuts reference."""
        lines = [
            "Keyboard Shortcuts:",
            "",
            "Execution Modes:",
            "  Shift+Tab       - Toggle between Architect/Execute modes",
            "  /mode           - Show current mode info",
            "  /mode architect - Switch to Architect mode (plan first)",
            "  /mode execute   - Switch to Execute mode (immediate action)",
            "",
            "Message Input:",
            "  Enter           - Send message (single line) or submit",
            "  Shift+Enter     - Insert new line (multiline input)",
            "  Escape          - Clear input field",
            "",
            "Navigation:",
            "  Page Up         - Scroll conversation up",
            "  Page Down       - Scroll conversation down",
            "  Mouse Wheel     - Scroll conversation",
            "",
            "Text Selection:",
            "  Ctrl+S          - Enable text selection mode",
            "  Mouse Drag      - Select text (when enabled)",
            "",
            "General:",
            "  Ctrl+C          - Exit application",
            "  /help           - Show command list",
        ]
        return "\n".join(lines)


class RichToFormattedTextConverter:
    """Convert Rich renderables to prompt_toolkit FormattedText."""
    
    @staticmethod
    def convert_markdown(markdown_text: str | None) -> list[tuple[str, str]]:
        """Convert markdown to formatted text tuples.

        Args:
            markdown_text: Markdown text to convert, or None for empty result

        Returns:
            List of (style_class, text) tuples for FormattedText.
        """
        # Handle None input gracefully
        if markdown_text is None:
            return []

        if not RICH_AVAILABLE:
            # Fallback: return plain text
            result = []
            for line in markdown_text.split('\n'):
                result.append(('class:ai-text', f"  {line}\n"))
            return result
        
        try:
            # Create Rich console for rendering
            console = Console(width=68, legacy_windows=False, force_terminal=True, force_interactive=False)
            
            # Render markdown
            md = Markdown(markdown_text, code_theme="monokai")
            
            with console.capture() as capture:
                console.print(md)
            
            rendered = capture.get()
            
            # Convert to formatted text
            result = []
            for line in rendered.split('\n'):
                result.append(('class:ai-text', f"  {line}\n"))
            
            logger.debug(f"Rendered {len(result)} lines of markdown")
            return result
            
        except Exception as e:
            logger.error(f"Markdown conversion failed: {e}", exc_info=True)
            # Fallback to plain text
            result = []
            for line in markdown_text.split('\n'):
                result.append(('class:ai-text', f"  {line}\n"))
            return result


class ConversationProcessor(Processor):
    """Custom processor to apply line-by-line formatting to conversation text.

    This processor works with FormattedBufferControl to display formatted text
    in a BufferControl, which provides native scrolling and text selection support.
    """

    def apply_transformation(self, transformation_input):
        """Apply formatting to a single line of text.

        Args:
            transformation_input: Contains buffer_control and line number

        Returns:
            Transformation with formatted text for the requested line
        """
        # Cast to FormattedBufferControl to access formatted_lines attribute
        control = cast(FormattedBufferControl, transformation_input.buffer_control)
        formatted_lines = control.formatted_lines
        lineno = transformation_input.lineno
        max_lineno = len(formatted_lines) - 1

        # Handle edge case where line number exceeds formatted lines
        if lineno > max_lineno:
            lineno = max_lineno if max_lineno >= 0 else 0

        # Get formatted text for this line
        line = formatted_lines[lineno] if formatted_lines else [("", "")]
        return Transformation(to_formatted_text(FormattedText(line)))


class FormattedBufferControl(BufferControl):
    """BufferControl subclass that supports formatted text display.

    This stores both plain text (in the buffer) and formatting metadata
    (in formatted_lines), allowing the ConversationProcessor to apply
    formatting line-by-line during rendering.
    """

    formatted_lines: list[list[tuple[str, str]]]

    def __init__(self, formatted_text, **kwargs):
        """Initialize with formatted text.

        Args:
            formatted_text: FormattedText to display
            **kwargs: Additional arguments for BufferControl
        """
        self.formatted_lines = self._parse_formatted_text(formatted_text)
        super().__init__(**kwargs)

    def _parse_formatted_text(self, formatted_text):
        """Transform formatted text with newlines into a list of lines.

        Each element in the returned list represents one line of text
        with its formatting metadata.

        Args:
            formatted_text: FormattedText containing style-text tuples

        Returns:
            List of formatted text lines
        """
        lines = []
        line = []

        for format_item in formatted_text:
            style, text, *_ = format_item
            word = []

            for char in text:
                if char != '\n':
                    word.append(char)
                    continue

                # Found newline - finish current word and line
                if word:
                    line.append((style, ''.join(word)))
                    lines.append(line)
                elif line:
                    lines.append(line)
                else:
                    lines.append([("", "")])

                line = []
                word = []

            # Add remaining word to current line
            if word:
                line.append((style, ''.join(word)))

        # Add final line if any
        if line:
            lines.append(line)

        return lines if lines else [[("", "")]]


class ConversationControl:
    """Manages conversation messages for display with BufferControl backend."""

    def __init__(self):
        self.messages: list[tuple[str, str, datetime]] = []  # (role, content, timestamp)
        self.streaming_message: Optional[str] = None
        self.streaming_role: Optional[str] = None
        self.system_info: Optional[str] = None  # For model info, warnings, etc.
        self.debug_mode: bool = False  # Debug mode flag for enhanced logging
        
        # Initialize Rich converter if available
        if RICH_AVAILABLE:
            self.converter = RichToFormattedTextConverter()
        else:
            self.converter = None

        # Create buffer and control for display
        self.buffer = Buffer(read_only=True)
        formatted_text = self.get_formatted_text()
        self.control = FormattedBufferControl(
            buffer=self.buffer,
            formatted_text=formatted_text,
            input_processors=[ConversationProcessor(), HighlightSelectionProcessor()],
            include_default_input_processors=False,
            focusable=False,  # Not focusable - scrolling via key bindings
            focus_on_click=False,
        )

        # Initialize buffer content
        self._update_buffer()

    def add_message(self, role: str, content: str):
        """Add a complete message to conversation history."""
        if role == "system":
            # System messages go to system_info, not conversation
            self.system_info = content
        else:
            self.messages.append((role, content, datetime.now()))
            self._update_buffer()

    def clear_messages(self):
        """Clear all conversation messages."""
        count = len(self.messages)
        self.messages.clear()
        self.streaming_message = None
        self.streaming_role = None
        logger.info(f"Cleared {count} messages from conversation")
        self._update_buffer()

    def start_streaming(self, role: str):
        """Start a new streaming message."""
        self.streaming_role = role
        self.streaming_message = ""

    def append_streaming(self, chunk: str):
        """Append content to the currently streaming message."""
        if self.streaming_message is not None:
            self.streaming_message += chunk
            self._update_buffer()

    def finish_streaming(self):
        """Finish streaming and add message to conversation history."""
        if self.streaming_message is not None and self.streaming_role is not None:
            self.add_message(self.streaming_role, self.streaming_message)
            self.streaming_message = None
            self.streaming_role = None
            # Note: add_message already calls _update_buffer()

    def get_formatted_text(self) -> FormattedText:
        """Generate formatted text for all messages.

        Returns FormattedText compatible with prompt_toolkit display.
        """
        result = []

        # Show empty state if no messages
        if not self.messages and self.streaming_message is None:
            result.append(("class:dim", "\n"))
            result.append(("class:dim", "  No messages yet.\n"))
            result.append(("class:dim", "  Type your message below and press Enter to start.\n"))
            result.append(("class:dim", "  Type /help to see available commands.\n"))
            result.append(("class:dim", "\n"))
            return FormattedText(result)

        # Display all complete messages
        for role, content, timestamp in self.messages:
            time_str = timestamp.strftime("%H:%M:%S")

            if role == "user":
                result.append(("class:user-label", f"\n  You · {time_str}\n"))
                result.append(("class:user-border", "  " + "─" * 70 + "\n"))
                # Add padding to content lines
                for line in content.split("\n"):
                    result.append(("class:user-text", f"  {line}\n"))
            
            elif role == "assistant":
                result.append(("class:ai-label", f"\n  GerdsenAI · {time_str}\n"))
                result.append(("class:ai-border", "  " + "─" * 70 + "\n"))
                
                # Try Rich rendering if available
                if self.converter:
                    try:
                        formatted = self.converter.convert_markdown(content)
                        # Add padding to each formatted line
                        for style, text in formatted:
                            # Add padding to the beginning of each line
                            padded_text = "\n".join(f"  {line}" if line else "" for line in text.split("\n"))
                            result.append((style, padded_text))
                    except Exception as e:
                        # Fallback to plain text on error
                        logger.warning(f"Rich rendering failed, using plain text: {e}")
                        for line in content.split("\n"):
                            result.append(("class:ai-text", f"  {line}\n"))
                else:
                    # Plain text fallback when Rich not available
                    for line in content.split("\n"):
                        result.append(("class:ai-text", f"  {line}\n"))
            
            elif role == "command":
                result.append(("class:command-label", f"\n  Command Result · {time_str}\n"))
                result.append(("class:command-border", "  " + "─" * 70 + "\n"))
                # Add padding to command result lines
                for line in content.split("\n"):
                    result.append(("class:command-text", f"  {line}\n"))

        # Display streaming message if active
        if self.streaming_message is not None and self.streaming_role is not None:
            time_str = datetime.now().strftime("%H:%M:%S")
            result.append(("class:ai-label", f"\n  GerdsenAI · {time_str} [streaming]\n"))
            result.append(("class:ai-border", "  " + "─" * 70 + "\n"))
            # Add padding to streaming content
            for line in self.streaming_message.split("\n"):
                result.append(("class:ai-text", f"  {line}\n"))
            result.append(("class:cursor", "  ▌"))  # Streaming cursor

        result.append(("", "\n"))
        return FormattedText(result)

    def _update_buffer(self):
        """Update buffer content and formatted lines when conversation changes.

        This method:
        1. Generates formatted text from current messages
        2. Extracts plain text for the buffer
        3. Updates formatted_lines in the control for the processor
        """
        # Get current formatted text
        formatted_text = self.get_formatted_text()

        # Convert to plain text for the buffer
        plain_text = fragment_list_to_text(formatted_text)

        # Update buffer with plain text
        self.buffer.set_document(Document(plain_text, 0), bypass_readonly=True)

        # Update formatted lines in the control for the processor
        self.control.formatted_lines = self.control._parse_formatted_text(formatted_text)


class PromptToolkitTUI:
    """prompt_toolkit-based TUI with embedded input.

    This provides a persistent chat interface where:
    - The layout is always visible
    - Input happens directly in the TUI (no external prompt)
    - Messages stream in real-time
    - Conversation uses Claude CLI-style sticky-bottom scrolling
    """

    def __init__(self):
        self.conversation = ConversationControl()
        self.input_buffer = Buffer(multiline=True)  # Support multiline input
        self.status_text = "Ready. Type your message and press Enter."
        self.system_footer_text = ""  # For model info, context window, etc.
        self.running = False
        self.message_callback: Optional[Callable[[str], Awaitable[None]]] = None
        self.command_callback: Optional[Callable[[str, list[str]], Awaitable[str]]] = None
        self.conversation_window: Optional[Window] = None  # Store reference for scrolling
        self.input_window: Optional[Window] = None  # Store reference for dynamic height
        self.auto_scroll_enabled = True  # Track if we should auto-scroll on updates
        
        # Initialize mode manager
        self.mode_manager = ModeManager(default_mode=ExecutionMode.ARCHITECT)
        logger.info(f"TUI initialized in {self.mode_manager.get_mode().value} mode")

        # Create keybindings
        self.kb = self._create_keybindings()

        # Create layout
        self.layout = self._create_layout()

        # Create application
        self.app = Application(
            layout=self.layout,
            key_bindings=self.kb,
            style=STYLE,
            full_screen=True,
            mouse_support=True,
        )

    def _is_at_bottom(self) -> bool:
        """Check if viewport is currently scrolled to bottom.

        Returns True if we're within 3 lines of the actual bottom.
        This implements Claude CLI-style sticky scrolling behavior.
        """
        if not self.conversation_window or not self.conversation_window.render_info:
            return True  # Default to bottom if not rendered yet

        render_info = self.conversation_window.render_info
        content_height = render_info.content_height or 0
        window_height = render_info.window_height or 1
        current_scroll = getattr(self.conversation_window, 'vertical_scroll', 0)
        max_scroll = max(0, content_height - window_height)

        # Consider "at bottom" if within 3 lines of actual bottom
        return current_scroll >= max_scroll - 3

    def _create_keybindings(self) -> KeyBindings:
        """Create keyboard shortcut handlers."""
        kb = KeyBindings()

        @kb.add('c-c')
        def exit_app(event):
            """Exit application on Ctrl+C."""
        @kb.add('enter')
        def submit_message(event):
            """Submit message on Enter key."""
            buffer = event.current_buffer
            text = buffer.text.strip()

            if text:
                # Check if this is a command
                if CommandParser.is_command(text):
                    command, args = CommandParser.parse(text)
                    logger.info(f"Processing command: {command} with args: {args}")
                    
                    # Handle built-in commands
                    if command in ['/exit', '/quit']:
                        event.app.exit()
                        return
                    
                    elif command == '/help':
                        help_text = CommandParser.get_help_text()
                        self.conversation.add_message("command", help_text)
                    
                    elif command == '/clear':
                        self.conversation.clear_messages()
                        self.conversation.add_message("command", "Conversation cleared.")
                    
                    elif command == '/debug':
                        self.conversation.debug_mode = not self.conversation.debug_mode
                        status = "enabled" if self.conversation.debug_mode else "disabled"
                        if self.conversation.debug_mode:
                            logger.setLevel(logging.DEBUG)
                        else:
                            logger.setLevel(logging.INFO)
                        self.conversation.add_message("command", f"Debug mode {status}.")
                        logger.info(f"Debug mode {status}")
                    
                    elif command == '/shortcuts':
                        shortcuts_text = CommandParser.get_shortcuts_text()
                        self.conversation.add_message("command", shortcuts_text)
                    
                    elif command == '/mode':
                        if not args:
                            # Show current mode
                            current_mode = self.mode_manager.get_mode()
                            mode_name = current_mode.value.title()
                            description = self.mode_manager.get_mode_description()
                            
                            message = (
                                f"Current Mode: {mode_name}\n\n"
                                f"{description}\n\n"
                                "Use '/mode architect' or '/mode execute' to switch modes.\n"
                                "Or press Shift+Tab to toggle."
                            )
                            self.conversation.add_message("command", message)
                        else:
                            # Switch mode
                            mode_arg = args[0].lower()
                            if mode_arg == 'architect':
                                self.mode_manager.set_mode(ExecutionMode.ARCHITECT)
                                description = self.mode_manager.get_mode_description(ExecutionMode.ARCHITECT)
                                self.conversation.add_message("command", f"Switched to Architect Mode\n\n{description}")
                                self.status_text = "Architect Mode active"
                            elif mode_arg == 'execute':
                                self.mode_manager.set_mode(ExecutionMode.EXECUTE)
                                description = self.mode_manager.get_mode_description(ExecutionMode.EXECUTE)
                                self.conversation.add_message("command", f"Switched to Execute Mode\n\n{description}")
                                self.status_text = "Execute Mode active"
                            else:
                                self.conversation.add_message("command", f"Unknown mode: {mode_arg}\n\nAvailable modes: architect, execute")
                    
                    else:
                        # External command - use callback if set
                        callback = self.command_callback
                        if callback:
                            async def handle_command():
                                try:
                                    response = await callback(command, args)
                                    self.conversation.add_message("command", response)
                                    self._auto_scroll_to_bottom()
                                except Exception as e:
                                    logger.error(f"Command callback error: {e}", exc_info=True)
                                    self.conversation.add_message("command", f"Error: {str(e)}")
                            asyncio.ensure_future(handle_command())
                        else:
                            self.conversation.add_message("command", f"Unknown command: {command}")
                else:
                    # Regular message
                    self.conversation.add_message("user", text)

                    # Trigger callback if set
                    if self.message_callback:
                        asyncio.ensure_future(self.message_callback(text))

                # Re-enable auto-scroll when user submits new message
                self.auto_scroll_enabled = True
                self._auto_scroll_to_bottom()

                # Clear input buffer
                buffer.reset()

                # Invalidate to trigger redraw
                event.app.invalidate()
                # Invalidate to trigger redraw
                event.app.invalidate()

        @kb.add('escape')
        def clear_input(event):
            """Clear input field on Escape."""
            event.current_buffer.reset()

        @kb.add('pageup')
        def scroll_up(event):
            """Scroll conversation up on Page Up.

            With BufferControl, we manipulate the cursor position to scroll.
            Moving cursor up causes the view to scroll up naturally.
            """
            # Disable auto-scroll when user manually scrolls
            self.auto_scroll_enabled = False

            # Move cursor up by approximately one page
            if self.conversation.buffer:
                # Calculate approximate lines per page (use window height if available)
                lines_to_move = 10
                if self.conversation_window and self.conversation_window.render_info:
                    window_height = self.conversation_window.render_info.window_height or 10
                    lines_to_move = max(1, window_height - 2)

                # Move cursor up in the buffer
                current_pos = self.conversation.buffer.cursor_position
                new_pos = max(0, current_pos - (lines_to_move * 50))  # Approximate chars per line
                self.conversation.buffer.cursor_position = new_pos
                event.app.invalidate()

        @kb.add('pagedown')
        def scroll_down(event):
            """Scroll conversation down on Page Down.

            With BufferControl, we manipulate the cursor position to scroll.
            Moving cursor down causes the view to scroll down naturally.
            """
            if self.conversation.buffer:
                # Calculate approximate lines per page
                lines_to_move = 10
                if self.conversation_window and self.conversation_window.render_info:
                    window_height = self.conversation_window.render_info.window_height or 10
                    lines_to_move = max(1, window_height - 2)

                # Move cursor down in the buffer
                current_pos = self.conversation.buffer.cursor_position
                text_length = len(self.conversation.buffer.text)
                new_pos = min(text_length, current_pos + (lines_to_move * 50))  # Approximate chars per line
                self.conversation.buffer.cursor_position = new_pos

                # Re-enable auto-scroll if we've reached the bottom
                if new_pos >= text_length - 10:  # Within 10 chars of end
                    self.auto_scroll_enabled = True

                event.app.invalidate()

        @kb.add('c-s')
        def suspend_for_text_selection(event):
            """Suspend TUI to allow text selection/copying (Ctrl+S)."""
            # Exit the application temporarily
            # This allows the user to select and copy text from the terminal
            # User can restart the TUI after copying
            event.app.exit()

        @kb.add('s-tab')  # Shift+Tab
        def toggle_mode(event):
            """Toggle between Architect and Execute modes."""
            new_mode = self.mode_manager.toggle_mode()
            mode_name = new_mode.value.title()
            description = self.mode_manager.get_mode_description(new_mode)
            
            message = f"Switched to {mode_name} Mode\n\n{description}"
            self.conversation.add_message("command", message)
            
            # Update status
            self.status_text = f"{mode_name} Mode active"
            
            event.app.invalidate()

        return kb

    def _create_layout(self) -> Layout:
        """Create the TUI layout structure.

        Layout consists of:
        - Header (fixed, 1 line)
        - Conversation (flexible, scrollable)
        - Input (fixed, 3 lines with frame)
        - System footer (conditional)
        - Status bar (fixed, 1 line)
        """

        # Header window
        header = Window(
            content=FormattedTextControl(
                text=lambda: FormattedText([
                    ("class:header", "  GerdsenAI CLI - Interactive Chat Mode · Type /help for commands  "),
                ])
            ),
            height=1,
            style="class:header-bg",
        )

        # Conversation window - BufferControl with formatted text processor
        # Uses FormattedBufferControl with native scrolling and text selection
        self.conversation_window = Window(
            content=self.conversation.control,
            wrap_lines=True,  # Let prompt_toolkit handle wrapping
            always_hide_cursor=True,
            scroll_offsets=ScrollOffsets(top=0, bottom=0),
            right_margins=[ScrollbarMargin(display_arrows=True)],
        )

        # Input field with buffer control (dynamic height 1-5 lines)
        self.input_window = Window(
            content=BufferControl(
                buffer=self.input_buffer,
                input_processors=[],
            ),
            height=lambda: min(5, max(1, self.input_buffer.text.count('\n') + 1)),
        )

        # Wrap input in a frame
        input_frame = Frame(
            body=self.input_window,
            title="Type your message (Enter to send, Shift+Enter for newline, Esc to clear)",
        )

        # System info footer (for model info, warnings, context window, etc.)
        system_footer = Window(
            content=FormattedTextControl(
                text=lambda: FormattedText([
                    ("class:system-footer", f"  {self.system_footer_text}" if self.system_footer_text else "")
                ])
            ),
            height=lambda: 1 if self.system_footer_text else 0,  # Hide when empty
            style="class:system-footer-bg",
        )

        # Status bar window
        scroll_indicator = " [SCROLLED UP ↑]" if not self._is_at_bottom() else ""
        status_window = Window(
            content=FormattedTextControl(
                text=lambda: FormattedText([
                    ("class:status", f"  {self.mode_manager.format_status_line()} | {len(self.conversation.messages)} messages{scroll_indicator} | {self.status_text} | Scroll: mouse/PgUp/PgDn | Ctrl+S: copy text | Ctrl+C: exit  ")
                ])
            ),
            height=1,
            style="class:status-bg",
        )

        # Combine into vertical split
        root_container = HSplit([
            header,                   # Fixed at top
            self.conversation_window, # Takes remaining space (scrollable)
            input_frame,              # Fixed above system footer
            system_footer,            # System info (model, warnings)
            status_window,            # Fixed at bottom
        ])

        return Layout(root_container)

    def set_message_callback(self, callback: Callable[[str], Awaitable[None]]):
        """Set callback function called when user submits a message.

        Args:
            callback: Async function that takes message text as argument
        """
        self.message_callback = callback

    def set_command_callback(self, callback: Callable[[str, list[str]], Awaitable[str]]):
        """Set callback function called when user submits a command.

        Args:
            callback: Async function that takes command and args, returns response
        """
        self.command_callback = callback

    def set_system_footer(self, text: str):
        """Set system footer text (model info, warnings, etc).

        Args:
            text: Text to display in system footer
        """
        self.system_footer_text = text
        self.app.invalidate()

    def clear_system_footer(self):
        """Clear the system footer."""
        self.system_footer_text = ""
        self.app.invalidate()

    def get_mode(self) -> ExecutionMode:
        """Get the current execution mode.
        
        Returns:
            Current ExecutionMode (ARCHITECT or EXECUTE)
        """
        return self.mode_manager.get_mode()

    def _auto_scroll_to_bottom(self):
        """Scroll conversation buffer to bottom if auto-scroll is enabled.

        This moves the buffer cursor to the end of the text, which causes
        BufferControl to scroll naturally to show the cursor position.
        """
        if self.auto_scroll_enabled and self.conversation.buffer:
            # Move cursor to end of buffer text
            text_length = len(self.conversation.buffer.text)
            self.conversation.buffer.cursor_position = text_length

    def start_streaming_response(self):
        """Begin streaming an AI response.

        Call this before streaming chunks to initialize the streaming message.
        """
        self.conversation.start_streaming("assistant")
        self.status_text = "AI is responding..."
        self.auto_scroll_enabled = True
        self._auto_scroll_to_bottom()
        self.app.invalidate()

    def append_streaming_chunk(self, chunk: str):
        """Append a chunk to the streaming AI response.

        Args:
            chunk: Text chunk to append to current streaming message
        """
        self.conversation.append_streaming(chunk)
        self._auto_scroll_to_bottom()
        self.app.invalidate()

    def finish_streaming_response(self):
        """Complete the streaming AI response.

        Converts streaming message to a complete message in conversation history.
        """
        self.conversation.finish_streaming()
        self.status_text = "Ready. Type your message and press Enter."
        self._auto_scroll_to_bottom()
        self.app.invalidate()

    async def run(self):
        """Run the TUI application.

        This blocks until the user exits (Ctrl+C or programmatic exit).
        """
        self.running = True
        try:
            await self.app.run_async()
        finally:
            self.running = False

    def exit(self):
        """Exit the application programmatically."""
        if self.running:
            self.app.exit()


# Color scheme for the TUI
STYLE = Style.from_dict({
    'header': 'bg:#008888 #ffffff bold',
    'header-bg': 'bg:#006666',
    'status': '#ffffff',
    'status-bg': 'bg:#444444',
    'user-label': '#00ffff bold',
    'user-border': '#00aaaa',
    'user-text': '#ffffff',
    'ai-label': '#00ff00 bold',
    'ai-border': '#00aa00',
    'ai-text': '#ffffff',
    'command-label': '#ffaa00 bold',
    'command-border': '#aa8800',
    'command-text': '#ffddaa',
    'system-label': '#ffaa00 bold',
    'system-border': '#aa8800',
    'system-text': '#ffddaa',
    'system-footer': '#888888',  # Dim gray for system info
    'system-footer-bg': 'bg:#2a2a2a',  # Dark gray background
    'cursor': '#ffff00 blink',
    'dim': '#888888 italic',
})
