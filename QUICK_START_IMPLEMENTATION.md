# Quick Start Guide - Implementing Claude-like Behavior

## TL;DR
Your CLI is 80% there. Main gap: **too much friction**. Users shouldn't need slash commands.

## 🎯 Goal
**Make this work:**
```
User: "explain the agent.py file"
AI: [auto-reads agent.py] "Here's what agent.py does..."
```

**Instead of current:**
```
User: "/read agent.py"
User: "explain this"
AI: "Here's what it does..."
```

---

## 🚀 Quick Wins (Start Here)

### 1. Auto File Reading (Easiest Win)

**Location:** `gerdsenai_cli/core/agent.py`, method `process_user_input()`

**Add this logic:**
```python
async def process_user_input(self, user_input: str) -> str:
    # NEW: Detect file mentions
    mentioned_files = self._extract_file_paths(user_input)

    if mentioned_files:
        # Show what we're doing
        console.print(f"[dim]📖 Reading {', '.join(mentioned_files)}...[/dim]")

        # Auto-read them
        for file_path in mentioned_files:
            content = await self._read_file_safe(file_path)
            # Inject into context
            context_prompt += f"\n\n# File: {file_path}\n{content}"

    # Continue with existing flow...
```

**Add helper method:**
```python
def _extract_file_paths(self, text: str) -> List[str]:
    """Extract potential file paths from user input."""
    import re

    # Pattern 1: Explicit file extensions
    patterns = [
        r'\b\w+\.(py|js|ts|java|cpp|md|txt|json|yaml)\b',
        r'\b[\w/]+/[\w.]+\b',  # Path-like structures
    ]

    found_files = []
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        found_files.extend(matches)

    # Validate files exist in project
    return [f for f in found_files if self.context_manager.file_exists(f)]
```

**Test:**
```bash
$ gerdsenai
> explain agent.py
📖 Reading agent.py...
[AI explains the file automatically]
```

---

### 2. Make Slash Commands Optional (Medium Effort)

**Location:** `gerdsenai_cli/main.py`, method `_handle_user_input()`

**Current logic:**
```python
async def _handle_user_input(self, user_input: str) -> bool:
    if user_input.startswith("/"):
        return await self._handle_command(user_input)
    else:
        return await self._handle_chat(user_input)
```

**Enhanced logic:**
```python
async def _handle_user_input(self, user_input: str) -> bool:
    # Explicit slash command
    if user_input.startswith("/"):
        return await self._handle_command(user_input)

    # NEW: Check for implicit commands
    implicit_command = self._detect_implicit_command(user_input)
    if implicit_command:
        # Convert to slash command and execute
        return await self._handle_command(implicit_command)

    # Regular chat
    return await self._handle_chat(user_input)

def _detect_implicit_command(self, user_input: str) -> Optional[str]:
    """Detect implicit commands from natural language."""
    lower_input = user_input.lower().strip()

    # Command patterns
    patterns = {
        r'^list (?:all )?files': '/files',
        r'^show (?:me )?files': '/files',
        r'^read (.+)': lambda m: f'/read {m.group(1)}',
        r'^edit (.+)': lambda m: f'/edit {m.group(1)}',
        r'^create (?:a )?file (.+)': lambda m: f'/create {m.group(1)}',
        r'^search for (.+)': lambda m: f'/search {m.group(1)}',
        r'^(?:show|display) history': '/history',
        r'^clear history': '/clear-history',
    }

    for pattern, command in patterns.items():
        match = re.match(pattern, lower_input)
        if match:
            # If command is a function, call it with match
            return command(match) if callable(command) else command

    return None
```

**Test:**
```bash
$ gerdsenai
> list files
[Shows file list - same as /files]

> read main.py
[Shows main.py content - same as /read main.py]
```

---

### 3. Streaming with Status (Polish)

**Location:** `gerdsenai_cli/core/agent.py`, method `process_user_input()`

**Current:**
```python
console.print("[bold cyan]\nGerdsenAI:[/bold cyan]", end=" ")
async for chunk in self.llm_client.stream_chat(llm_messages):
    if chunk:
        llm_response += chunk
        console.print(chunk, end="", style="white")
```

**Enhanced (like Claude):**
```python
# Show thinking indicator briefly
with console.status("[dim]Thinking...[/dim]", spinner="dots"):
    await asyncio.sleep(0.1)  # Brief pause for UX

# Stream response with better formatting
console.print()  # Newline
async for chunk in self.llm_client.stream_chat(llm_messages):
    if chunk:
        llm_response += chunk
        console.print(chunk, end="", style="white")
console.print()  # Final newline
```

---

## 🎨 UX Improvements

### Show What You're Doing
```python
# Before destructive operation
console.print("[yellow]📝 Preparing to edit main.py...[/yellow]")

# During file read
console.print("[dim]📖 Reading files: main.py, utils.py[/dim]")

# After success
console.print("[green]✓[/green] Done!")
```

### Confirm Intelligently
```python
def needs_confirmation(self, operation: ActionType) -> bool:
    """Determine if operation needs user confirmation."""
    # Never confirm reads
    if operation in [ActionType.READ_FILE, ActionType.SEARCH_FILES]:
        return False

    # Always confirm destructive ops
    if operation in [ActionType.EDIT_FILE, ActionType.DELETE_FILE]:
        return True

    # Create files: confirm only if exists
    if operation == ActionType.CREATE_FILE:
        return file_exists(target_path)

    return False
```

---

## 📝 Testing Checklist

After implementing changes:

### Basic Flow Tests
- [ ] `explain agent.py` → auto-reads and explains
- [ ] `list files` → shows files (no slash needed)
- [ ] `edit main.py add logging` → prepares edit
- [ ] `/read main.py` → still works (backward compat)

### Edge Cases
- [ ] `tell me about xyz.py` (nonexistent file) → graceful error
- [ ] `edit all test files` → multi-file support or clear message
- [ ] Empty input → no crash
- [ ] Ctrl+C during stream → clean cancel

### UX Polish
- [ ] Status indicators show during operations
- [ ] Colors are readable
- [ ] No double-newlines or formatting glitches
- [ ] Streaming feels smooth (no buffer delays)

---

## 🔧 Configuration Options

Add to `config/settings.py`:

```python
class Settings(BaseModel):
    # ... existing fields ...

    # NEW: Behavior toggles
    auto_read_files: bool = Field(
        default=True,
        description="Automatically read files mentioned in conversation"
    )

    require_slash_commands: bool = Field(
        default=False,
        description="Require explicit /command syntax (power user mode)"
    )

    proactive_context: str = Field(
        default="moderate",
        description="How aggressively to build context: conservative|moderate|aggressive"
    )
```

User can toggle:
```bash
> /config set auto_read_files false
> /config set require_slash_commands true  # "strict mode"
```

---

## ⚠️ Gotchas

### 1. Context Window Limits
Auto-reading files can quickly fill the LLM context. Monitor token usage:

```python
MAX_AUTO_READ_FILES = 5
MAX_AUTO_READ_SIZE = 50_000  # characters

if len(mentioned_files) > MAX_AUTO_READ_FILES:
    console.print(f"[yellow]⚠️ Only reading first {MAX_AUTO_READ_FILES} files[/yellow]")
    mentioned_files = mentioned_files[:MAX_AUTO_READ_FILES]
```

### 2. False Positives
Not every "file-like" word is a file:

```python
# Bad: Treats "main.py" in this sentence as a file
"I think the main.py should implement the Handler class"

# Good: Check if file exists before auto-reading
if self.context_manager.file_exists(potential_file):
    # It's a real file
```

### 3. Performance
Reading many large files is slow:

```python
# Add timeout
try:
    content = await asyncio.wait_for(
        self._read_file(path),
        timeout=2.0  # 2 second limit per file
    )
except asyncio.TimeoutError:
    console.print(f"[yellow]⚠️ {path} too large, skipping[/yellow]")
```

---

## 🎓 Learning from Claude CLI

**What Claude does right:**
1. **Zero friction** - No commands to remember
2. **Confirms intent** - "I'll read these files for you..."
3. **Shows work** - "Reading X... Editing Y..."
4. **Fails gracefully** - "I couldn't find that file. Did you mean...?"
5. **Context-aware** - Remembers what you're working on

**Implement in order:**
1. Auto file reading (easiest, biggest impact)
2. Implicit command detection (medium effort)
3. Better status messages (easy polish)
4. Multi-file awareness (advanced)
5. Persistent memory (nice-to-have)

---

## 🚦 Start Here

1. **Copy auto file reading snippet** into `agent.py`
2. **Test with:** `explain agent.py`
3. **Iterate** based on what feels natural
4. **Add implicit commands** once comfortable
5. **Polish UX** with status messages

**Time estimate:** 4-6 hours for basic version

---

## 📚 Full Details

See `ALIGNMENT_ANALYSIS.md` for:
- Complete architectural analysis
- All 4 implementation phases
- Trade-off discussions
- Socratic questions for design decisions

**Questions?** All design rationale documented there.
