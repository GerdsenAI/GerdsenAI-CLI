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
- **Done:** first-run setup (`main._first_time_setup`) auto-offers discovered
  local + tailnet servers to pick from, falling back to manual host/port entry
  when nothing is found or the user declines.

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
- **Retrieval is wired into the agent**: when `enable_vector_index` is on,
  `Agent._build_project_context` appends a "Semantic Search Results" block from
  the index (`Agent._retrieve_semantic_context`); no-op otherwise.
- **Incremental re-indexing**: `/index refresh` (alias `update`) re-embeds only
  files whose content hash changed since the last build, removes chunks for
  deleted files, and skips unchanged ones — tracked via a per-collection
  manifest under `~/.config/gerdsenai-cli/index/`. `/index build` still does a
  full rebuild; `/index clear` drops the manifest too.

## Skill / agent-file import — **implemented**
- `core/skill_loader.py` discovers, read-only, `.claude/skills/*/SKILL.md`
  (frontmatter parsed without a PyYAML dependency), `.claude/agents/*.md`, and
  `AGENTS.md` from the project dir and the user's home (project wins on conflict).
- Each becomes an **invocable slash command** (`/<skill-name>`, prints the
  skill's instructions) registered at startup without clobbering built-ins, and
  a compact summary is injected into the agent's system prompt
  (`Agent.skills_context`).
- `/skills` (alias `/agents`) lists them; `/skills show <name>` prints the full
  text; `/skills reload` re-scans.
- **Follow-up:** optional auto-application of a skill's full body into context
  when its topic is detected.

## Agent ↔ provider/model binding — **implemented**
- `core/agent_profiles.py`: named personas (`AgentProfile`) bind a system prompt
  to a provider + model, persisted in settings (`agent_profiles`,
  `active_agent_profile`).
- `/persona` (alias `/profile`): `list`, `add <name> <model> [provider]`,
  `system <name> <prompt>`, `use <name>` (also switches `current_model`),
  `show`, `current`, `remove`. The active persona's prompt is folded into the
  agent's system prompt (`Agent.persona_context`) at startup and on switch.
- **Provider routing is wired**: when the active persona's `provider` is
  `anthropic`, the agent's send path (`_complete_response` / `_stream_response`)
  routes through the Anthropic provider; otherwise it uses the configured local
  `llm_client` unchanged. Falls back to local if the SDK/key are unavailable.

## Anthropic provider (optional, local stays default) — **implemented**
- `ProviderType.ANTHROPIC` + `core/providers/anthropic.py` use the `anthropic`
  SDK with **prompt caching** (`cache_control` on the system prompt) and
  streaming. Sampling params are omitted for models that reject them (Opus
  4.7/4.8). Default model `claude-opus-4-8` (`anthropic_model` setting).
- **Secrets via the OS keyring** (`core/secrets.py`, `keyring`) with an
  `ANTHROPIC_API_KEY` env fallback — **never** written to `config.json`.
- Optional install: `pip install "gerdsenai-cli[anthropic]"`. Surfaced via the
  `/anthropic` command (alias `/claude`): `status`, `set-key`, `clear-key`,
  `models`, `model`, `chat`. Degrades to a friendly no-op when the SDK/key are
  absent.
- **Done:** the agent's send path routes through the Anthropic provider when a
  `claude-*` model is selected directly (or a persona is bound to `anthropic`);
  see `Agent._route_provider`. Falls back to local if the SDK/key are absent.
- **Follow-up:** richer Anthropic features on that path (tool use, thinking,
  batch).

## Security hardening
- `core/secrets.py` provides keyring-backed secret storage (done, used by the
  Anthropic provider). Remaining: revisit `core/terminal.py` shell execution
  (currently allow/block lists + per-command confirmation); keep the
  confirmation gates.

## Test coverage
- Coverage is currently ~45% (the pytest gate was lowered from an aspirational 90%
  to match reality). Raising real coverage back toward 90% is tracked here as
  ongoing work, prioritising `core/agent.py`, `commands/`, and the providers.

## Agentic tool-use loop — **in progress**
- Turning the agent from a single-shot intent classifier into a real
  tool→observe→tool loop. Landed: native tool-calling in the LLM client
  (`chat_with_tools`, `ToolCall`/`ChatResult`), Anthropic `tool_use`, and a
  prompt-based tool shim (`core/tool_shim.py`) so tool-less local models still work.
- Landed (engine): `core/tool_registry.py` — `Tool`, `ToolRegistry`, and
  `run_agent_loop` (bounded loop; read-only tools run freely, mutating tools gated
  by a `confirm` callback; CHAT mode = no tools; `max_iterations` cap).
- Landed (wire-in + UX): the loop drives both `process_user_input` and the
  streaming TUI path, surfacing reasoning/tool/answer events live; model-compat
  layer (`core/tool_parsing.py`) handles OpenAI, Hermes `<tool_call>` XML, the
  shim, and `<think>` reasoning.
- Landed (MCP tools): configured MCP servers are exposed to the loop as tools via
  the **optional** `mcp` extra — `pip install "gerdsenai-cli[mcp]"`. `core/mcp_client.py`
  (streamable-HTTP wrapper, lazy-imported, degrades to no-op when the SDK is absent
  or the server is unreachable) + `core/mcp_tools.py` (`build_mcp_tools` wraps each
  server tool as `mcp__<server>__<tool>`, `mutating=True` so it passes the confirm
  gate). `/mcp connect` lists a server's tools for real; `Agent._ensure_tool_registry`
  merges them into the default registry (cached per session).
- **Next:** diff-based edits and unifying the duplicated TUI streaming loops; MCP
  stdio transport (the SDK gives it to us for free).

## Process notes
- **GitHub PR creation depends on a working GitHub connection.** Branches always
  push over plain git, but opening/merging PRs needs the GitHub integration
  connected. If it drops mid-session, restore it via the Claude
  directory/integrations and complete the OAuth flow using **only** the genuine
  `localhost/callback?code=...` URL from that flow — never a callback pointing at a
  different service. (A prior session saw the connection drop and a spurious
  "switch to a Google Drive endpoint" message, which was correctly refused; the
  GitHub connection later recovered on its own.)
