# Verifying GerdsenAI-CLI

Two layers of verification back every change to the agentic loop:

1. **Automated, deterministic** — the shared harness in `tests/harness.py` drives the
   *real* agent tool-loop over a `tmp_path` project with a scripted (no-network) LLM, so
   read→edit→final behavior, autonomy gating, and streaming are pinned in CI.
2. **Manual, real-model** — drive the actual TUI against a local model to confirm the
   experience (live thinking, tool stream, file changes, cancel) end-to-end. This page is
   the recipe each feature PR repeats.

---

## 1. Automated: the test harness

`tests/harness.py` is the one place tests get a fake LLM client and a real `Agent`:

```python
from tests.harness import ScriptedLLMClient, build_agent, tool_call, final, run_turn

client = ScriptedLLMClient([
    tool_call("read_file", path="hello.py"),
    tool_call("edit_file", path="hello.py", new_content="print('new')\n"),
    final("Updated hello.py."),
])
agent = build_agent(tmp_path, client, mode="execute")
result = await run_turn(agent, "make hello.py print new")

assert result.tools_run == ["read_file", "edit_file"]
assert result.files_modified == 1
```

- **`ScriptedLLMClient(script, *, chat_reply=...)`** — pops scripted `ChatResult`s from
  `chat_with_tools` (the native tool-loop path); `chat` / `stream_chat` return `chat_reply`
  (CHAT / single-shot path). Advertises native tool support, so no monkeypatch is needed.
  Telemetry: `chat_calls`, `tool_calls`, `stream_calls`, `last_messages`, `last_tools`.
- **`build_agent(tmp_path, client, *, mode=..., preferences=...)`** — a real `Agent` with
  hermetic backups under `tmp_path`, intent detection off, context pre-built. `mode` is the
  autonomy dial (`chat` / `architect` / `execute` / `llvl`).
- **`tool_call(name, **args)` / `final(text, *, reasoning="")`** — `ChatResult` builders.
- **`run_turn` / `run_turn_stream`** — drive one user turn and return a `TurnResult`
  (`text`, `tools_run`, `files_modified`).

Run it:

```bash
pytest tests/test_harness.py tests/test_agent_loop_wiring.py tests/test_agent_loop_streaming.py -q
```

---

## 2. Manual: drive the real TUI against a local model

Prereqs: a local LLM server (e.g. Ollama) running a tool-capable model
(`qwen2.5-coder`, `hermes`, `llama3.1`, …). Use the `/run` and `/verify` skills to launch
and observe.

```bash
ollama serve &              # or vLLM / LM Studio / TGI
ollama pull qwen2.5-coder   # a model that supports function-calling
gerdsenai                   # launches the TUI; /setup if the server isn't auto-detected
```

### Recipe A — read → edit in one turn (the core loop)

1. In a scratch project, create `hello.py` containing `print("old")`.
2. Ask: **"make hello.py print 'new' instead"**.
3. **Look for:**
   - a dim, collapsible **thinking** block (toggle with the thinking key) — reasoning is
     stripped from parsing and shown separately, never as the answer;
   - **`⚙ read_file(...)`** then **`⚙ edit_file(...)`** status lines streaming live (not a
     frozen spinner);
   - a **diff preview + confirm** before the write (consent gate);
   - `hello.py` actually contains `print("new")` on disk afterward;
   - a final natural-language answer.

### Recipe B — autonomy modes

- **ARCHITECT**: every mutating tool prompts for confirmation.
- **EXECUTE**: edits auto-apply, but **`run_command` still always prompts** (the security
  non-negotiable — verify by asking it to run a shell command).
- **CHAT**: no tools offered; a plain conversational reply.

### Recipe C — cancel mid-chain

1. Ask for a multi-step task that will make several tool calls.
2. Press **Escape** while it's streaming.
3. **Look for:** the loop stops promptly, partial output is kept, a dim `⏹ cancelled` note
   appears, and input focus returns — no traceback, no stuck UI.

---

## Per-PR checklist

Before pushing any loop-touching change, all of these exit 0:

```bash
ruff check gerdsenai_cli/
ruff format --check gerdsenai_cli/
mypy gerdsenai_cli/core/agent.py gerdsenai_cli/core/tool_registry.py \
     gerdsenai_cli/core/tool_parsing.py gerdsenai_cli/core/agent_tools.py \
     gerdsenai_cli/core/llm_client.py gerdsenai_cli/utils/performance.py   # core-loop gate
pytest                       # coverage >= gate
python -m build && twine check dist/*
```

Then run the manual recipe above against a live local model and confirm the behaviors
listed. The automated harness proves the wiring; the manual pass proves the experience.
