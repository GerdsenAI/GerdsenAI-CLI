# Roadmap

GerdsenAI CLI is **local-AI-first**: it talks to local model servers (Ollama,
vLLM, LM Studio, HuggingFace TGI) over HTTP and degrades gracefully when optional
services are absent. This roadmap records the planned capabilities and the design
decisions already made, so future work can proceed without re-litigating them.

> Status: **planned** unless noted. Each capability must **no-op gracefully** when
> its backing service (Tailscale, Qdrant, an Anthropic key, an embedding backend)
> is unavailable.

## Local model auto-discovery
- **Today:** `core/providers/detector.py` scans hardcoded localhost ports for
  Ollama (11434), LM Studio (1234), vLLM (8000), HF TGI (8080), and a few others.
- **Planned:** cross-platform local detection plus **Tailscale peer discovery** —
  enumerate peers via `tailscale status --json`, then probe provider ports on each
  reachable peer. Surface results via a `/discover` command and offer auto-config
  on first run. No-op when the `tailscale` CLI is absent.

## Per-repo vector index (Qdrant)
- Auto-detect a local Qdrant (default `:6333`); create **one collection per repo**
  and index the working tree for retrieval into agent context.
- **Embeddings = Ollama-first:** use an Ollama embedding model when Ollama is
  present (no new hard dependency); offer `sentence-transformers` as an **optional
  extra**. Degrade to a no-op when neither Qdrant nor an embedding backend exists.
- New module: `core/vector_store.py`; indexing hook in `core/context_manager.py`;
  retrieval folded into the agent's context assembly.

## Skill / agent-file import
- Discover `.claude/skills/*/SKILL.md` (YAML frontmatter), `AGENTS.md`, and Codex
  configs from the working tree.
- **Behavior:** expose each as an **invocable slash command** *and* inject relevant
  ones into the system prompt as context. Read-only — no arbitrary execution.
- New module: `core/skill_loader.py`, registering through the existing
  `CommandRegistry` (`commands/parser.py`).

## Agent ↔ provider/model binding
- Allow binding a named agent/persona to a specific provider + model, so different
  tasks can route to different local (or remote) models.

## Anthropic provider (optional, local stays default)
- Add `ProviderType.ANTHROPIC` and `core/providers/anthropic.py` using the
  `anthropic` SDK, with **prompt caching** enabled.
- **Secrets via the OS keyring** (`keyring`: macOS Keychain / Linux Secret Service)
  with an `ANTHROPIC_API_KEY` environment-variable fallback. Keys are **never**
  written to `config.json`.

## Security hardening
- Revisit `core/terminal.py` shell execution (currently allow/block lists +
  per-command confirmation); keep the confirmation gates and add the keyring-backed
  secret storage above.

## Test coverage
- Coverage is currently ~45% (the pytest gate was lowered from an aspirational 90%
  to match reality). Raising real coverage back toward 90% is tracked here as
  ongoing work, prioritising `core/agent.py`, `commands/`, and the providers.
