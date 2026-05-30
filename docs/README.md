# GerdsenAI CLI Documentation

Documentation hub for GerdsenAI CLI — a terminal-based agentic coding tool for
local AI models (Ollama, vLLM, LM Studio, HuggingFace TGI).

> **Development setup:** create and activate a virtual environment first —
> a fresh clone does not ship one:
> ```bash
> python3.11 -m venv .venv && source .venv/bin/activate
> pip install -e ".[dev]"
> ```

---

## Getting Started
- **[Main README](../README.md)** — overview, installation, quick start
- **[Quick Start Guide](development/QUICK_START_IMPLEMENTATION.md)** — fast track
- **[Contributing Guide](development/CONTRIBUTING.md)** — how to contribute

## Development
- **[Testing Guide](development/TESTING_GUIDE.md)** — running and writing tests
- **[Security Improvements](development/SECURITY_IMPROVEMENTS.md)** — security notes
- **[Conversation Commands](development/CONVERSATION_COMMANDS.md)** — slash commands
- **[Slash Commands](development/SLASH_COMMAND.MD)** — detailed command reference
- **[Next Steps Planning](development/NEXT_STEPS_PLANNING.md)** — near-term plans

## Features & Architecture
- **[Smart Router Integration](SMART_ROUTER_INTEGRATION.md)** — intent routing
- **[Vision Integration](VISION_INTEGRATION.md)** — OCR / vision plugins
- **[TUI Troubleshooting](TUI_TROUBLESHOOTING.md)** — fixing terminal UI issues

## Project Management
- **[Roadmap](ROADMAP.md)** — planned capabilities and design decisions
- **[TODO](TODO.md)** — current task tracking
- **[Agent Guide (CLAUDE.md)](../CLAUDE.md)** — conventions for AI agents

> **Historical docs.** Completed phase reports, audits, and superseded plans
> have been moved to **[`archive/`](archive/)** to keep this index focused on
> living documentation. They are kept for reference, not as current guidance.

---

## Quick Reference

```bash
source .venv/bin/activate

# Run
gerdsenai                       # start the TUI
gerdsenai --help                # show help

# Quality gates
ruff check gerdsenai_cli/       # lint
ruff format gerdsenai_cli/      # format
mypy gerdsenai_cli/             # type check
pytest                          # tests
```

### Common Slash Commands (in the TUI)
`/help` `/status` `/config` `/discover` `/index` `/skills` `/models`
`/model <name>` `/edit` `/create` `/search` `/mcp` `/clear` `/exit`

---

## License

MIT — see [LICENSE](../LICENSE).

## Links
- **Repository:** [GerdsenAI/GerdsenAI-CLI](https://github.com/GerdsenAI/GerdsenAI-CLI)
- **Issues:** [Report bugs / request features](https://github.com/GerdsenAI/GerdsenAI-CLI/issues)
