# Roadmap

GerdsenAI CLI is **local-AI-first**: it talks to local model servers (Ollama,
vLLM, LM Studio, HuggingFace TGI) over HTTP and degrades gracefully when optional
services are absent. This roadmap records the planned capabilities and the design
decisions already made, so future work can proceed without re-litigating them.

> Status: **planned** unless noted. Each capability must **no-op gracefully** when
> its backing service (Tailscale, Qdrant, an Anthropic key, an embedding backend)
> is unavailable.

## Local model auto-discovery — **implemented**
- `core/providers/detector.py` scans localhost ports for Ollama (11434),
  LM Studio (1234), vLLM (8000), HF TGI (8080), and a few others.
- **Tailscale peer discovery** (`core/providers/tailscale.py`): enumerates online
  peers via `tailscale status --json`, then probes the provider ports on each
  reachable peer. No-op when the `tailscale` CLI is absent or the tailnet is down.
- Surfaced via the **`/discover`** command (aliases `/scan`, `/find-models`):
  lists local + tailnet servers with their models, and `--configure` sets the
  first one as the active provider. `--no-tailscale` restricts to localhost.
- **Follow-up:** offer discovery automatically on first-run setup.

## Per-repo vector index (Qdrant) — **implemented (indexing + search)**
- Auto-detects a local Qdrant (default `:6333`, accessed over its REST API via
  `httpx` — no `qdrant-client` dependency) and creates **one collection per repo**
  (`core/vector_store.py`, `core/repo_index.py`).
- **Embeddings = Ollama-first** (`core/embeddings.py`): uses an Ollama embedding
  model when available (no new hard dependency); `sentence-transformers` is an
  **optional extra** (`pip install "gerdsenai-cli[embeddings]"`). Degrades to a
  no-op when neither Qdrant nor an embedding backend exists.
- Surfaced via the **`/index`** command: `build`, `status`, `search <query>`,
  `clear`. Settings: `enable_vector_index`, `qdrant_url`, `embedding_model`,
  `vector_index_chunk_chars`.
- **Follow-up:** fold semantic retrieval into the agent's context assembly
  (`agent._prepare_llm_messages`) when `enable_vector_index` is on, and add
  incremental re-indexing of changed files.

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
