# GerdsenAI CLI Commands

Here's the consolidated list of GerdsenAI CLI commands with clear, single-purpose commands and minimal aliases.

## System & Configuration
* `/help` - Display help information and available commands.
  * Alias: `/?`
* `/quit` - Exit GerdsenAI CLI.
  * Alias: `/q`
* `/setup` - Interactive reconfiguration of LLM server connection.
* `/config` - View or modify configuration settings.
  * Actions: show, set, get
* `/status` - View current system status and health information.
* `/debug` - Toggle debug mode on/off.
* `/about` - Show version info for troubleshooting.

## Chat & Memory Management
* `/chat` - Manage conversation state and history.
  * Actions: show, clear, save, load
* `/memory` - Manage AI's instructional memory.
  * Actions: add, show, refresh
* `/clear` - Clear terminal screen (Ctrl+L to trigger).
* `/reset` - Reset agent session and clear context.
  * Options: --keep-context

## File Operations
* `/files` - List files in the current project directory.
  * Alias: `/ls`
  * Options: --detailed, --filter
* `/read` - Read and display the contents of a file.
  * Alias: `/cat`
  * Options: --lines, --syntax
* `/edit` - Edit a file with AI assistance.
  * Options: --backup
* `/create` - Create a new file with specified content.
  * Options: --template
* `/search` - Search for text patterns across project files.
  * Alias: `/find`
  * Options: --path, --extension, --limit

## Model Management
* `/model` - Select or change the AI model.
  * Usage: `/model <model_name>`
* `/models` - List all available models from the LLM server.
  * Options: --detailed, --filter

## Agent Management
* `/agent` - Display current agent status and statistics.
  * Options: --detailed
* `/agents` - Manage custom AI subagents for specific tasks.
* `/refresh` - Refresh the project context and file cache.
  * Options: --deep

## Session Management
* `/session` - Manage work sessions and project state.
  * Actions: save, load, list, delete

## Project & Workspace
* `/directory` - Manage workspace directories.
  * Actions: add, show
* `/tools` - List available tools in CLI.
  * Options: desc, nodesc

## Utilities
* `/bug` - Report a bug or issue (default to GitHub repository).
* `/cost` - Show token usage statistics.
* `/review` - Request a code review.
* `/theme` - Change the CLI's visual theme.

## MCP Integration
* `/mcp` - Manage Model Context Protocol (MCP) server connections.
  * Options: desc, nodesc, schema

## Not Yet Implemented (See TODO.md)
* `/init` - Initialize a project with a GerdsenAI.md guide.
* `/settings` - Open settings editor to modify CLI preferences.
* `/auth` - Change authentication method.
* `/compress` - Replace current chat context with a summary.
* `/copy` - Copy last output to clipboard.
* `/restore` - Restore project files to previous state.
* `/extensions` - List active extensions in the current session.
* `/permissions` - View or update permissions.
* `/pr_comments` - View pull request comments.
* `/vim` - Toggle vim mode for editing.
* `/stats` - Show session statistics (different from /cost).
* `/checkup` - Check the health of your GerdsenAI Code installation.

## Command Aliases Summary
* `/?` → `/help`
* `/q` → `/quit`  
* `/ls` → `/files`
* `/cat` → `/read`
* `/find` → `/search`

---

**Note**: This document reflects the consolidated command structure. Some commands may require code updates to match this specification.
