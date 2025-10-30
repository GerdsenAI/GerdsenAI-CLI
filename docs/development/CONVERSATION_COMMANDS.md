# Conversation Management Commands

GerdsenAI CLI now supports saving, loading, and exporting your conversations!

## Available Commands

### Save Conversation

Save your current conversation to a JSON file:

```
/save <filename>
```

**Example:**
```
/save important_discussion
```

This saves your conversation to `~/.gerdsenai/conversations/important_discussion.json`

**Notes:**
- Filename is required
- `.json` extension is added automatically
- Includes metadata (model, message count, timestamp)
- Conversation must have at least one message

### Load Conversation

List all saved conversations:

```
/load
```

Load a specific conversation:

```
/load <filename>
```

**Example:**
```
/load important_discussion
```

**Notes:**
- Without filename, lists all available conversations
- With filename, clears current conversation and loads saved messages
- Displays conversation metadata
- Use tab completion for filenames (if available)

### Export to Markdown

Export your conversation to a readable markdown file:

```
/export [filename]
```

**Examples:**
```
/export meeting_notes
/export
```

**Notes:**
- Filename is optional
- Without filename, generates timestamp-based name (e.g., `conversation_20251004_120000.md`)
- `.md` extension is added automatically
- Exports to `~/.gerdsenai/exports/`
- Includes all messages with timestamps
- Includes metadata section
- Great for sharing or documentation

## File Locations

All conversation files are stored in your home directory:

```
~/.gerdsenai/
 conversations/     # JSON files (.json)
    chat1.json
    debug_session.json
    project_planning.json
 exports/          # Markdown files (.md)
     conversation_20251004_120000.md
     important_discussion.md
```

## Metadata

Saved conversations include metadata:

- **model**: AI model used (e.g., "qwen/qwen3-4b-2507")
- **message_count**: Number of messages in conversation
- **created_at**: Timestamp when conversation was created
- **exported_at**: Timestamp when conversation was exported (exports only)

## Workflow Examples

### Save Work in Progress

```
# During a long conversation
/save work_in_progress

# Come back later and continue
/load work_in_progress
```

### Create Documentation

```
# After completing a planning session
/export project_plan

# Opens: ~/.gerdsenai/exports/project_plan.md
# Share with team or add to documentation
```

### Backup Important Conversations

```
# Save critical conversations
/save bug_fix_discussion
/save feature_requirements

# List them later
/load
```

### Compare Conversations

```
# Save conversation with model A
/model model-a
# ... have conversation ...
/save test_model_a

# Switch to model B
/model model-b
# ... have same conversation ...
/save test_model_b

# Export both for comparison
/load test_model_a
/export comparison_model_a

/load test_model_b
/export comparison_model_b
```

## Tips

1. **Descriptive Names**: Use clear, descriptive filenames
   - Good: `/save api_design_discussion`
   - Avoid: `/save chat1`

2. **Regular Saves**: Save frequently during long sessions
   - Protects against crashes
   - Creates checkpoints you can return to

3. **Export for Sharing**: Use `/export` when you need to share conversations
   - Markdown is readable in any text editor
   - Easy to copy/paste into documentation
   - Version control friendly

4. **Organize by Project**: Use consistent naming conventions
   - `/save project_name_topic`
   - `/save project_name_date`

5. **Clean Up Old Conversations**: Periodically review and remove old conversations
   - Files are stored in `~/.gerdsenai/conversations/`
   - Safe to delete old JSON files manually

## Model Switching

Switch AI models during your session:

```
/model <model-name>
```

**Example:**
```
/model qwen/qwen3-4b-2507
```

Show current model:

```
/model
```

**Note**: Model changes are saved in conversation metadata, so you can see which model was used when loading old conversations.

## Troubleshooting

### "No messages to save"
- You need at least one message in the conversation
- Send a message first, then save

### "Conversation not found"
- Check filename spelling
- Use `/load` without arguments to list available conversations
- Ensure the file exists in `~/.gerdsenai/conversations/`

### "Error: TUI not available"
- This error shouldn't occur in normal use
- Restart the application if you see it

### File Permission Issues
- Ensure `~/.gerdsenai/` directory is writable
- Check disk space

## Data Format

### JSON Format (`.json` files)

```json
{
  "version": "1.0",
  "created_at": "2025-10-04T12:00:00",
  "messages": [
    {
      "role": "user",
      "content": "Hello!",
      "timestamp": "2025-10-04T12:00:01"
    },
    {
      "role": "assistant",
      "content": "Hi there!",
      "timestamp": "2025-10-04T12:00:02"
    }
  ],
  "metadata": {
    "model": "qwen/qwen3-4b-2507",
    "message_count": 2
  }
}
```

### Markdown Format (`.md` files)

```markdown
# GerdsenAI Conversation

## Metadata

- **model**: qwen/qwen3-4b-2507
- **message_count**: 2

---

## User (12:00:01)

Hello!

## GerdsenAI (12:00:02)

Hi there!
```

## Security & Privacy

- All conversations are stored locally on your machine
- No data is sent to external servers
- Files are created with user-only permissions
- You control what to save and export
- Safe to version control (if appropriate for your use case)

## Advanced Usage

### Backup All Conversations

```bash
# Create backup of all conversations
tar -czf conversations_backup.tar.gz ~/.gerdsenai/conversations/

# Restore from backup
tar -xzf conversations_backup.tar.gz -C ~/
```

### Search Conversations

```bash
# Search all conversations for a term
grep -r "search term" ~/.gerdsenai/conversations/

# Find conversations by model
grep -l "model.*gpt-4" ~/.gerdsenai/conversations/*.json
```

### Batch Export

```bash
# Export all conversations to markdown
for json in ~/.gerdsenai/conversations/*.json; do
  name=$(basename "$json" .json)
  # Use CLI to load and export each
done
```

## Keyboard Shortcuts

While in TUI mode:

- **Enter**: Send message or execute command
- **Escape**: Clear input field
- **Page Up**: Scroll conversation up
- **Page Down**: Scroll conversation down
- **Ctrl+C**: Interrupt AI response
- **Ctrl+D**: Exit application

## Getting Help

For more information:

```
/help           # Show all available commands
/shortcuts      # Show keyboard shortcuts
```

## Future Enhancements

Planned features:

- Conversation search within TUI
- Tagging and categorization
- Conversation merging
- Import from other formats
- Conversation statistics
- Interactive conversation browser
