GerdsenAI CLI Commands
Here’s an optimized list of the GerdsenAI CLI commands with concise descriptions and improved organization.
System & Authentication
* /initInitialize a project with a GerdsenAI.md guide.
* /settingsOpen settings editor to modify CLI preferences.
* /authChange authentication method.
* /aboutShow version info for troubleshooting.
Conversation & Memory Management
* /chatManage conversation state (save, resume, list, delete).
    * save: Save current chat state with a <tag>.
    * resume: Resume a conversation from a saved checkpoint.
    * list: List available conversation checkpoints.
    * delete: Delete a specific conversation checkpoint.
* /clearClear terminal screen (Ctrl+L to trigger).
* /compressReplace current chat context with a summary.
* /copyCopy last output to clipboard.
* /memoryManage AI’s instructional memory.
    * add: Add text to memory.
    * show: View current memory context.
    * refresh: Reload memory from all GerdsenAI.md files.
Project & File Management
* /directoryManage workspace directories.
    * add: Add a directory to workspace.
    * show: Show added directories.
* /restoreRestore project files to previous state before a tool was executed.
* /extensionsList active extensions in the current session.
* /toolsList available tools in CLI.
    * desc: Show detailed tool descriptions.
    * nodesc: Hide tool descriptions.
Model & Agent Management
* /modelSelect or change the AI model.
* /agentsManage custom AI subagents for specific tasks.
* /mcpManage Model Context Protocol (MCP) server connections.
    * desc: Show MCP server and tool descriptions.
    * nodesc: Hide MCP tool descriptions.
    * schema: Show full JSON schema for tool parameters.
Utility & Debugging
* /bugReport a bug or issue (default to GitHub repository).
* /statusView current system statuses.
* /checkupCheck the health of your GerdsenAI Code installation.
* /costShow token usage statistics (see cost guide for details).
* /permissionsView or update permissions.
* /pr_commentsView pull request comments.
* /reviewRequest a code review.
CLI Customization
* /themeChange the CLI’s visual theme.
* /vimToggle vim mode for editing.
Exiting & Help
* /helpDisplay help information and available commands.
* /quitExit GerdsenAI CLI.
* /?Alias for /help.
Miscellaneous
* /configView or modify the configuration settings.
* /statsShow session statistics (token usage, cached tokens, etc.).
* /directory showList all directories added for multi-directory support.
