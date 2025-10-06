# GerdsenAI CLI Examples

This directory contains example configurations and workflows to help you get started with GerdsenAI CLI.

---

## 📁 Directory Structure

```
examples/
├── config/           # Configuration file examples
│   ├── basic.json           # Minimal configuration for getting started
│   ├── power-user.json      # Advanced configuration with all features
│   └── mcp-github.json      # Configuration with GitHub MCP server
└── workflows/        # Example usage workflows (coming soon)
```

---

## ⚙️ Configuration Examples

### 📄 basic.json
**Use case:** Getting started, local development, simple projects

Minimal configuration with sensible defaults:
- Local Ollama server
- Qwen 2.5 Coder 7B model
- Basic UI features
- Standard safety settings

```bash
# Use this config
python -m gerdsenai_cli --config examples/config/basic.json
```

### 🚀 power-user.json
**Use case:** Advanced users, large projects, maximum features

Full-featured configuration with:
- Larger model (32B)
- Extended context window (128K tokens)
- Advanced intelligence tracking
- Performance optimizations
- Comprehensive logging
- All UI features enabled

```bash
# Use this config
python -m gerdsenai_cli --config examples/config/power-user.json
```

### 🔗 mcp-github.json
**Use case:** GitHub integration, repository management

Configuration with Model Context Protocol (MCP) integration:
- GitHub MCP server enabled
- Medium-sized model (14B)
- Thinking mode enabled
- Auto-connect to MCP servers

**Prerequisites:**
```bash
# Set your GitHub token
export GITHUB_TOKEN="your_github_personal_access_token"

# Run with MCP integration
python -m gerdsenai_cli --config examples/config/mcp-github.json
```

---

## 🎯 Configuration Options

### API Settings
```json
{
  "api": {
    "base_url": "http://localhost:11434/v1",  // LLM server URL
    "api_key": "ollama",                       // API key (if required)
    "model": "qwen2.5-coder:7b",              // Model name
    "timeout": 300,                            // Request timeout (seconds)
    "max_retries": 3,                          // Max retry attempts
    "stream": true                             // Enable streaming responses
  }
}
```

### Conversation Settings
```json
{
  "conversation": {
    "max_context_messages": 50,                // Number of messages in context
    "context_window": 32000,                   // Token limit for context
    "preserve_system_message": true,           // Keep system message
    "auto_save": false,                        // Auto-save conversations
    "save_directory": "~/.gerdsenai/conversations"  // Save location
  }
}
```

### File Operations
```json
{
  "file_operations": {
    "auto_backup": true,                       // Automatically backup files
    "backup_directory": ".backups",            // Backup location
    "backup_count": 5,                         // Number of backups to keep
    "diff_preview": true,                      // Show diffs before applying
    "safe_mode": true                          // Extra safety checks
  }
}
```

### Terminal Settings
```json
{
  "terminal": {
    "auto_confirm": false,                     // Auto-confirm commands (dangerous!)
    "command_timeout": 60,                     // Command timeout (seconds)
    "shell": "zsh",                           // Shell to use
    "allow_dangerous_commands": false          // Block dangerous commands
  }
}
```

### UI Settings
```json
{
  "ui": {
    "theme": "default",                        // Color theme
    "show_timestamps": true,                   // Show message timestamps
    "show_token_count": false,                 // Show token counts
    "thinking_enabled": false,                 // Display AI thinking process
    "animation_enabled": true,                 // Enable animations
    "syntax_highlighting": true                // Syntax highlighting for code
  }
}
```

### Intelligence Tracking
```json
{
  "intelligence": {
    "enabled": true,                           // Enable intelligence features
    "learning_rate": 0.1,                      // Learning rate for patterns
    "track_patterns": true,                    // Track usage patterns
    "analyze_context": true,                   // Analyze context
    "suggest_improvements": true               // Suggest improvements
  }
}
```

### MCP (Model Context Protocol)
```json
{
  "mcp": {
    "enabled": true,                           // Enable MCP integration
    "servers": [                               // MCP server configurations
      {
        "name": "github",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-github"],
        "env": {
          "GITHUB_PERSONAL_ACCESS_TOKEN": "${GITHUB_TOKEN}"
        }
      }
    ],
    "auto_connect": false                      // Auto-connect on startup
  }
}
```

---

## 🔧 Custom Configuration

### Creating Your Own Config

1. **Copy a base config:**
   ```bash
   cp examples/config/basic.json my-config.json
   ```

2. **Edit settings:**
   ```bash
   # Use your favorite editor
   nano my-config.json
   ```

3. **Use your config:**
   ```bash
   python -m gerdsenai_cli --config my-config.json
   ```

### Default Config Location

If no `--config` is specified, GerdsenAI CLI looks for config in:
1. `./gerdsenai.json` (current directory)
2. `~/.gerdsenai/config.json` (user home)
3. Built-in defaults

### Environment Variables

You can use environment variables in configs:
```json
{
  "api": {
    "base_url": "${LLM_BASE_URL}",
    "api_key": "${LLM_API_KEY}"
  }
}
```

Then set them:
```bash
export LLM_BASE_URL="http://localhost:11434/v1"
export LLM_API_KEY="your-api-key"
```

---

## 🚀 Quick Start Recipes

### Local Development
```bash
# Basic setup for local coding
python -m gerdsenai_cli --config examples/config/basic.json
```

### Large Projects
```bash
# Power user setup with all features
python -m gerdsenai_cli --config examples/config/power-user.json
```

### GitHub Integration
```bash
# Setup with GitHub MCP server
export GITHUB_TOKEN="your_token"
python -m gerdsenai_cli --config examples/config/mcp-github.json
```

### Multiple Configs
```bash
# Switch between configs easily
alias gai-basic='python -m gerdsenai_cli --config examples/config/basic.json'
alias gai-power='python -m gerdsenai_cli --config examples/config/power-user.json'
alias gai-github='python -m gerdsenai_cli --config examples/config/mcp-github.json'

# Then use:
gai-basic   # Start with basic config
gai-power   # Start with power user config
```

---

## 📚 Related Documentation

- **[Configuration Guide](../docs/development/CONTRIBUTING.md)** - Detailed configuration documentation
- **[MCP Setup](../docs/features/MCP_INTEGRATION.md)** - Model Context Protocol setup
- **[Command Reference](../docs/development/CONVERSATION_COMMANDS.md)** - Available commands

---

## 💡 Tips

1. **Start Simple** - Use `basic.json` first, then customize
2. **Enable Thinking** - Set `thinking_enabled: true` for debugging
3. **Auto-save** - Enable `auto_save` to never lose conversations
4. **MCP Servers** - Add MCP servers for extended capabilities
5. **Backup Everything** - Always keep `auto_backup: true`

---

**Need Help?** Check the [main documentation](../docs/README.md) or open an issue!
