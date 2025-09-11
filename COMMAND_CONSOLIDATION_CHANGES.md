# Command Consolidation - Required Code Changes

This document outlines the specific code changes needed to implement the consolidated command structure defined in SLASH_COMMANDS.MD.

## Summary of Changes Needed

### 1. Command Class Renames and Updates

#### File: `gerdsenai_cli/commands/agent.py`

**Rename Classes:**
- `ConversationCommand` → `ChatCommand`
- `ClearSessionCommand` → `ResetCommand`

**Property Updates:**
```python
# ChatCommand (formerly ConversationCommand)
@property
def name(self) -> str:
    return "chat"  # was "conversation"

@property
def aliases(self) -> list[str]:
    return ["conv"]  # remove "chat-history"

# ResetCommand (formerly ClearSessionCommand)
@property
def name(self) -> str:
    return "reset"  # was "clear"

@property
def aliases(self) -> list[str]:
    return []  # was ["clear-session", "reset"]
```

#### File: `gerdsenai_cli/commands/files.py`

**Rename Classes:**
- `ListFilesCommand` → `FilesCommand`
- `ReadFileCommand` → `ReadCommand`

**Property Updates:**
```python
# FilesCommand (formerly ListFilesCommand)
@property
def name(self) -> str:
    return "files"  # was "ls"

@property
def aliases(self) -> list[str]:
    return ["ls"]  # was ["list", "files"]

# ReadCommand (formerly ReadFileCommand)
@property
def name(self) -> str:
    return "read"  # was "cat"

@property
def aliases(self) -> list[str]:
    return ["cat"]  # was ["read", "view"]
```

#### File: `gerdsenai_cli/commands/files.py`

**Update SearchFilesCommand:**
```python
@property
def aliases(self) -> list[str]:
    return ["find"]  # was ["grep", "find"]
```

### 2. Command Registration Updates

#### File: `gerdsenai_cli/main.py`

**Update Import Statements:**
```python
# Update imports
from .commands.agent import AgentStatusCommand, ChatCommand, RefreshContextCommand, ResetCommand, AgentConfigCommand
from .commands.files import FilesCommand, ReadCommand, EditFileCommand, CreateFileCommand, SearchFilesCommand, SessionCommand
```

**Update Command Registration:**
```python
# Replace old registrations with new ones
await self.command_parser.register_command(ChatCommand(**command_deps))          # was ConversationCommand
await self.command_parser.register_command(ResetCommand(**command_deps))         # was ClearSessionCommand
await self.command_parser.register_command(FilesCommand(**command_deps))         # was ListFilesCommand
await self.command_parser.register_command(ReadCommand(**command_deps))          # was ReadFileCommand
```

### 3. Missing Command Implementations Needed

#### High Priority Commands to Implement:

**File: `gerdsenai_cli/commands/system.py`**
- Add `AboutCommand` class for `/about`
- Add `InitCommand` class for `/init`

**File: `gerdsenai_cli/commands/agent.py`**
- Add `MemoryCommand` class for `/memory`

**File: `gerdsenai_cli/commands/files.py`**
- Add `ToolsCommand` class for `/tools`

**File: `gerdsenai_cli/commands/model.py`**
- Add `McpCommand` class for `/mcp`

### 4. Alias Consolidation

#### File: `gerdsenai_cli/commands/parser.py`

**Update alias handling to support the clean structure:**
```python
# Ensure these aliases work correctly:
COMMAND_ALIASES = {
    "?": "help",
    "q": "quit",
    "ls": "files",
    "cat": "read",
    "find": "search"
}
```

### 5. Help System Updates

#### Update help text in all command classes to match new structure:
- Remove references to old command names
- Update examples to use consolidated command names
- Ensure alias documentation is consistent

### 6. Remove Conflicting Commands

#### Issues to resolve:
- **`/clear` conflict**: Currently used for both screen clearing and session clearing
  - Solution: `/clear` for screen, `/reset` for session
- **Multiple aliases**: Remove excessive aliases, keep only essential ones

## Implementation Priority

### Phase 1 (Low Risk):
1. Update command class properties (name, aliases)
2. Update help text and descriptions
3. Update documentation references

### Phase 2 (Medium Risk):
1. Rename command classes
2. Update import statements
3. Update command registration

### Phase 3 (High Risk):
1. Implement missing high-priority commands
2. Test all command functionality
3. Update parser alias handling

## Testing Requirements

After implementing changes:
1. Test all renamed commands work with new names
2. Test all aliases function correctly
3. Test help system shows correct information
4. Test no duplicate commands exist
5. Test parser handles conflicts properly

## Files That Need Changes

1. `gerdsenai_cli/main.py` - Command registration updates
2. `gerdsenai_cli/commands/agent.py` - Class renames and property updates
3. `gerdsenai_cli/commands/files.py` - Class renames and property updates
4. `gerdsenai_cli/commands/system.py` - Add missing commands
5. `gerdsenai_cli/commands/parser.py` - Alias handling updates
6. `SLASH_COMMANDS.MD` - ✅ Already updated
7. `TODO.md` - ✅ Already updated

## Validation Checklist

- [ ] All commands from SLASH_COMMANDS.MD work as documented
- [ ] No duplicate command names exist
- [ ] All aliases function correctly
- [ ] Help system is consistent
- [ ] No conflicting commands remain
- [ ] All high-priority missing commands implemented
