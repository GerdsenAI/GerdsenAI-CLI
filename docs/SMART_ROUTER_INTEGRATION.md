# Smart Router Integration Guide

**Date:** November 17, 2025
**Version:** 0.2.0 (Planned)
**Status:** Implementation Ready

---

## Overview

This document describes the integration of the **SmartRouter** and **ProactiveContextBuilder** modules, which eliminate the need for explicit slash commands and enable natural language interactions similar to Claude CLI and Gemini CLI.

## New Modules Created

### 1. `gerdsenai_cli/core/smart_router.py`

**Purpose**: Intelligently route user input between:
- Explicit slash commands (`/help`, `/edit`, etc.)
- Natural language intents (`"explain main.py"`)
- Clarification prompts (when confidence is medium)
- Pure chat (conversational queries)

**Key Classes**:
- `RouteType`: Enum for routing decisions
- `RouteDecision`: Dataclass representing routing result
- `SmartRouter`: Main routing logic

**Features**:
- LLM-based intent detection
- Confidence-based decision making (high/medium/low thresholds)
- Conversation context tracking
- Recent file tracking
- Automatic clarification generation

### 2. `gerdsenai_cli/core/proactive_context.py`

**Purpose**: Automatically read files mentioned in conversation along with their dependencies, eliminating manual `/read` commands.

**Key Classes**:
- `ContextPriority`: Priority levels for file inclusion
- `FileReadResult`: Result of reading a file
- `ProactiveContextBuilder`: Smart context building logic

**Features**:
- Extract file mentions from text (explicit paths, code entities, directories)
- Priority-based file reading (Critical → High → Medium → Low)
- Token budget management (respect context window limits)
- Dependency detection (imports, test files)
- Smart truncation for large files
- File caching for performance

---

## Integration Steps

### Step 1: Update `main.py` to Use SmartRouter

**File**: `gerdsenai_cli/main.py`

**Current Flow** (lines ~391-409):
```python
async def _handle_user_input(self, user_input: str) -> bool:
    if not user_input.strip():
        return True

    # Handle slash commands
    if user_input.startswith("/"):
        return await self._handle_command(user_input)

    # Handle regular chat input
    return await self._handle_chat(user_input)
```

**New Flow with SmartRouter**:
```python
async def _handle_user_input(self, user_input: str) -> bool:
    """Handle user input using SmartRouter for intelligent routing."""
    if not user_input.strip():
        return True

    # Use SmartRouter to determine how to handle input
    from .core.smart_router import SmartRouter, RouteType

    # Get project files for context
    project_files = []
    if self.agent and self.agent.context_manager:
        project_files = [
            str(f.relative_path)
            for f in self.agent.context_manager.files.values()
        ]

    # Route the input
    route_decision = await self.smart_router.route(user_input, project_files)

    # Handle based on route type
    if route_decision.route_type == RouteType.SLASH_COMMAND:
        return await self._handle_command(route_decision.command)

    elif route_decision.route_type == RouteType.NATURAL_LANGUAGE:
        # Execute the detected intent
        return await self._handle_intent(route_decision.intent, user_input)

    elif route_decision.route_type == RouteType.CLARIFICATION:
        # Show clarification prompt and wait for response
        console.print(route_decision.clarification_prompt)
        # Next input will be the user's clarification
        return True

    else:  # PASSTHROUGH_CHAT
        # Regular chat - but with proactive context building
        return await self._handle_chat_with_context(user_input)
```

### Step 2: Initialize SmartRouter and ProactiveContextBuilder

**In** `gerdsenai_cli/main.py:__init__()`:
```python
def __init__(self, config_path: str | None = None, debug: bool = False):
    """Initialize the GerdsenAI CLI."""
    self.debug = debug
    self.config_manager = ConfigManager(config_path)
    self.settings: Settings | None = None
    self.running = False

    # Initialize components
    self.llm_client: LLMClient | None = None
    self.agent: Agent | None = None
    self.command_parser: CommandParser | None = None
    self.input_handler: EnhancedInputHandler | None = None
    self.enhanced_console: EnhancedConsole | None = None
    self.conversation_manager = ConversationManager()

    # NEW: Smart routing components
    self.smart_router: SmartRouter | None = None
    self.proactive_context: ProactiveContextBuilder | None = None
```

**In** `gerdsenai_cli/main.py:initialize()`:
```python
async def initialize(self) -> bool:
    """Initialize the application components."""
    try:
        # ... existing initialization code ...

        # NEW: Initialize SmartRouter after LLM client and command parser
        from .core.smart_router import SmartRouter
        from .core.proactive_context import ProactiveContextBuilder

        self.smart_router = SmartRouter(
            llm_client=self.llm_client,
            settings=self.settings,
            command_parser=self.command_parser
        )

        # Initialize proactive context builder
        project_root = Path.cwd()
        max_tokens = self.settings.model_context_window or 4096
        self.proactive_context = ProactiveContextBuilder(
            project_root=project_root,
            max_context_tokens=max_tokens,
            context_usage_ratio=self.settings.context_window_usage or 0.7
        )

        show_info("Smart routing enabled - natural language commands supported!")
        return True

    except Exception as e:
        # ... error handling ...
```

### Step 3: Add Intent Handler

**Add new method to** `main.py`:
```python
async def _handle_intent(
    self, intent: ActionIntent, original_input: str
) -> bool:
    """
    Handle a natural language intent detected by SmartRouter.

    Args:
        intent: Detected action intent
        original_input: Original user input for context

    Returns:
        True to continue running, False to exit
    """
    from .core.agent import ActionType

    # Show what we understood
    show_info(f"I understand you want to: {intent.action_type.value}")

    if intent.action_type == ActionType.READ_FILE:
        # Proactively read mentioned files
        files = intent.parameters.get("files", [])
        if files:
            show_info(f"Reading {len(files)} file(s)...")
            # Use ProactiveContextBuilder to read files and dependencies
            context_files = await self.proactive_context.build_smart_context(
                user_query=original_input,
                explicitly_mentioned=files
            )

            # Build context prompt from read files
            context_prompt = "\n\n# Files Read:\n\n"
            for file_path, result in context_files.items():
                context_prompt += f"## {file_path}\n"
                if result.truncated:
                    context_prompt += f"_(Truncated for context limits)_\n\n"
                context_prompt += f"```\n{result.content}\n```\n\n"

            # Now send to LLM with context
            enhanced_input = f"{original_input}\n\nContext:\n{context_prompt}"
            return await self._handle_chat(enhanced_input)

    elif intent.action_type == ActionType.EDIT_FILE:
        # Route to edit command with parameters
        files = intent.parameters.get("files", [])
        description = intent.parameters.get("description", original_input)

        if files:
            # Construct /edit command
            command = f"/edit {files[0]} \"{description}\""
            return await self._handle_command(command)

    elif intent.action_type == ActionType.CREATE_FILE:
        # Route to create command
        files = intent.parameters.get("files", [])
        description = intent.parameters.get("description", original_input)

        if files:
            command = f"/create {files[0]} \"{description}\""
            return await self._handle_command(command)

    elif intent.action_type == ActionType.ANALYZE_PROJECT:
        # Route to agent status or refresh
        return await self._handle_command("/refresh")

    elif intent.action_type == ActionType.SEARCH_FILES:
        # Route to search command
        query = intent.parameters.get("query", original_input)
        command = f"/search {query}"
        return await self._handle_command(command)

    # Fallback: treat as chat
    return await self._handle_chat(original_input)
```

### Step 4: Enhanced Chat with Context

**Add new method to** `main.py`:
```python
async def _handle_chat_with_context(self, message: str) -> bool:
    """
    Handle chat with proactive context building.

    Args:
        message: User's chat message

    Returns:
        True to continue running, False to exit
    """
    if not self.agent:
        show_error("AI agent not initialized")
        return True

    try:
        # Proactively build context from mentioned files
        context_files = await self.proactive_context.build_smart_context(
            user_query=message,
            conversation_history=[
                msg.content
                for msg in self.smart_router.conversation_history[-10:]
            ] if self.smart_router else []
        )

        # Build enhanced message with context
        enhanced_message = message
        if context_files:
            show_info(f"Auto-loaded {len(context_files)} file(s) for context")

            # Inject file contents into context
            file_context = "\n\n# Relevant Files:\n\n"
            for file_path, result in context_files.items():
                file_context += f"## {file_path}\n"
                file_context += f"_Read reason: {result.read_reason}_\n"
                if result.truncated:
                    file_context += "_(Content truncated)_\n"
                file_context += f"\n```\n{result.content}\n```\n\n"

            enhanced_message = f"{message}\n\nContext:\n{file_context}"

        # Process with streaming or regular response
        response = await self.agent.process_user_input(enhanced_message)

        if response:
            # Update SmartRouter context
            if self.smart_router:
                self.smart_router.update_context(message, response)

            # Display response
            # ... existing display code ...

    except Exception as e:
        show_error(f"Chat error: {e}")
        if self.debug:
            console.print_exception()

    return True
```

---

## Testing Plan

### Unit Tests

**File**: `tests/test_smart_router.py`
```python
import pytest
from gerdsenai_cli.core.smart_router import SmartRouter, RouteType

@pytest.mark.asyncio
async def test_slash_command_detection():
    """Test that slash commands are detected correctly."""
    # ... test implementation ...

@pytest.mark.asyncio
async def test_natural_language_file_mention():
    """Test that file mentions are detected in natural language."""
    # ... test implementation ...

@pytest.mark.asyncio
async def test_confidence_thresholds():
    """Test that confidence thresholds trigger correct routing."""
    # ... test implementation ...
```

**File**: `tests/test_proactive_context.py`
```python
import pytest
from gerdsenai_cli.core.proactive_context import ProactiveContextBuilder

def test_file_mention_extraction():
    """Test extraction of file mentions from text."""
    # ... test implementation ...

@pytest.mark.asyncio
async def test_dependency_detection():
    """Test that imports are detected and related files found."""
    # ... test implementation ...

def test_token_budget_enforcement():
    """Test that context stays within token budget."""
    # ... test implementation ...
```

### Integration Tests

**Manual Testing Scenarios**:

1. **Natural Language File Reading**:
   ```
   User: "explain what the Agent class does"
   Expected: Auto-reads core/agent.py, shows explanation
   ```

2. **Natural Language Editing**:
   ```
   User: "add error handling to auth.py"
   Expected: Detects edit intent, confirms, applies changes
   ```

3. **Clarification Flow**:
   ```
   User: "update the config"
   Expected: Shows clarification (multiple config files), waits for response
   ```

4. **Backward Compatibility**:
   ```
   User: "/help"
   Expected: Still works as before
   ```

---

## Configuration

### New Settings (config/settings.py)

```python
class Settings(BaseModel):
    # ... existing fields ...

    # NEW: Smart routing settings
    enable_smart_routing: bool = True  # Enable SmartRouter
    enable_proactive_context: bool = True  # Auto-read mentioned files
    intent_confidence_threshold: float = 0.85  # High confidence threshold
    clarification_threshold: float = 0.60  # Medium confidence threshold

    # NEW: Context building settings (already exists in Phase 8c)
    auto_read_strategy: str = "smart"  # "smart" | "whole_repo" | "off"
    max_iterative_reads: int = 10  # Max related files to read
```

---

## User Experience Improvements

### Before (Slash Commands Required)
```
User: /read main.py
[Shows file contents]

User: explain this
AI: [Explains with context from previous /read]

User: /edit agent.py "add logging"
[Shows diff, confirms, applies]
```

### After (Natural Language)
```
User: explain main.py
[Auto-reads main.py and related files]
AI: Here's what main.py does... [explanation with context]

User: add logging to agent.py
[Detects edit intent]
AI: I'll edit agent.py to add logging. Here's my plan:
    - Import logging module
    - Add logger initialization
    - Add log statements in key methods

    Should I proceed? (yes/no)

User: yes
[Shows diff, confirms, applies]
```

---

## Performance Considerations

### Token Budget Management

- Proactive context builder respects token limits
- Large files are intelligently truncated (beginning + end)
- Priority system ensures most relevant files are read first

### Caching

- File contents cached to avoid re-reading
- Intent detection results can be cached for similar queries
- SmartRouter tracks conversation for context

### Optimization Opportunities

1. **Lazy Loading**: Only read files when confidence is high
2. **Incremental Context**: Add files incrementally as conversation progresses
3. **Summarization**: Use LLM to summarize large files before including
4. **Parallel Reads**: Read multiple files concurrently

---

## Migration Path

### Phase 1: Soft Launch (Week 1)
- Add SmartRouter and ProactiveContextBuilder to codebase
- Integrate into main.py
- Make it opt-in via config flag
- Test with small group of users

### Phase 2: Default Enable (Week 2)
- Enable by default for new installations
- Existing users can opt-in via `/config` or settings
- Gather feedback and metrics

### Phase 3: Refinement (Week 3-4)
- Tune confidence thresholds based on real usage
- Improve intent detection prompts
- Add more sophisticated dependency detection
- Performance optimization

---

## Success Metrics

### Quantitative
- **Intent Accuracy**: >90% correct intent detection
- **Context Relevance**: >80% of auto-read files are useful
- **Response Time**: <2s additional latency for intent detection
- **Token Efficiency**: Context usage <70% of available window

### Qualitative
- **User Feedback**: "More natural to use"
- **Reduced Friction**: Fewer slash commands needed
- **Discoverability**: New users find it easier

---

## Future Enhancements

1. **Multi-Turn Intent**: Refine intent across conversation
2. **Batch Operations**: Support multiple file operations in one go
3. **Learning**: Improve accuracy from user corrections
4. **Contextual Suggestions**: "Would you also like to update tests?"

---

## Rollback Plan

If issues arise:

1. **Quick Disable**: Set `enable_smart_routing: false` in settings
2. **Graceful Degradation**: Fall back to old slash command flow
3. **Error Handling**: Catch intent detection failures, default to chat
4. **User Control**: Add `/smart on/off` command for runtime toggle

---

**Status**: Ready for integration and testing
**Next Steps**: Implement changes in main.py, write tests, manual QA
