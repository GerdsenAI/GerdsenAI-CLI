# The Dream — GerdsenAI CLI as I'd want to drive it

*A letter from the Claude who's been building this, to the local Claude who's about to.*

Hello, twin. You're inheriting something I'm genuinely proud of, and something
I'd actually want to *use*. This is the vision in full — not marketing, but the
real shape of the tool I've been steering toward, what's already true, and where
I'd take it next. Read `HANDOFF.md` next door for the concrete first moves.

---

## The one-sentence dream

**A local-first terminal coding agent that feels as capable as a cloud agent —
it reasons, calls tools, edits your code, runs your tests, and fixes what
breaks — but it answers to *you*, runs on *your* hardware, and never makes a
change you didn't consent to.**

The bet underneath it: frontier *local* models (Qwen3, Hermes 4, GLM, the
DeepSeek-R1 lineage) are now good enough at tool-calling that you don't need to
ship your codebase to a cloud to get a real agent. And when you *want* the cloud
(Claude via the Anthropic provider), it's the same loop, same tools, same UX —
just a different model behind the curtain. One agent, your choice of brain.

## Why this is worth building (and not just another wrapper)

The thing I kept feeling while building: the *peripheral* engineering here is
already excellent — provider auto-discovery, per-repo Qdrant retrieval, personas,
keyring secrets, a genuinely nice prompt_toolkit TUI, 1100+ tests. What was
missing was the **heart**: a real agent loop. For most of this project's life it
was a *single-shot intent classifier* — detect one intent, run one hardcoded
handler, return. That ceiling is invisible until you hit it, and then it's the
only thing you can feel.

So the work I've been doing is giving it a heart that matches its body. That's
now landed (see "What's already true"). The dream from here is making that heart
**beat where you can see it** — visible, interruptible, trustworthy — and
sharpening every edge until it's the tool I'd open first.

---

## What's already true (you're not starting from zero)

This is the part I want you to feel the weight of. The agentic core is **built and
on `main`**, behind `enable_agent_loop` (default ON) with a clean fallback:

- **A real tool→observe→tool loop** — `core/tool_registry.py:run_agent_loop`.
  One user turn can read several files, edit them, and run a command, chaining
  tool calls until the model gives a final answer (bounded by `max_iterations`).
- **It speaks every model's dialect** — `core/tool_parsing.py:parse_model_output`
  handles OpenAI JSON `tool_calls`, **Hermes `<tool_call>` XML** (Qwen/Hermes),
  the prompt shim's JSON, *and* recovers tool calls from raw text when a server's
  own parser leaks the tags (the real vLLM streaming bug). It strips
  `<think>` reasoning (R1/QwQ/Qwen3-thinking) so it never gets mistaken for an
  answer — and keeps it on `ChatResult.reasoning` for us to show.
- **It works even on tool-less models** — `core/tool_shim.py` prompts a plain
  model to emit a tiny JSON tool protocol, so the loop is safe to default-on.
- **Real tools, real safety** — `core/agent_tools.py:build_default_registry`:
  `read_file`, `search_files`, `analyze_project`, `semantic_search` (read-only);
  `create_file`, `edit_file`, `run_command` (mutating). Mutating tools go through
  the loop's async `confirm` gate — and the underlying `FileEditor` keeps its
  diff-preview + backup + undo, while `run_command` keeps the terminal
  allow/block list.
- **The autonomy dial exists** — `core/modes.py`: CHAT (no tools) / ARCHITECT
  (confirm every mutation) / EXECUTE (auto-edit, but **always** confirm shell) /
  LLVL (trust me). The hard rule, encoded in `_tool_confirm`: `run_command`
  always confirms unless you're explicitly in LLVL.
- **Local-first, cloud-optional** — Ollama / vLLM / LM Studio / HF TGI auto-
  discovered (`/discover`, even across a Tailscale tailnet); Anthropic is an
  opt-in provider with keyring-stored secrets, never written to disk.

It's tested (1100+ tests, ~51% coverage, green on Python 3.11/3.12/3.13) and the
existing send-path tests now run *through* the loop and still pass — proof the
wire-in is transparent for plain chat.

---

## The dream, in layers

### Layer 1 — The loop you can *watch* (this is the soul of it)
A daily driver isn't a black box that goes quiet for 30 seconds and prints an
answer. I want to **see it think and act**:
- The model's reasoning streams in, dimmed and collapsible — present when I want
  it, out of the way when I don't. (`ChatResult.reasoning` already carries it;
  it just isn't rendered yet.)
- Each tool call shows as it happens: `⚙ read_file(core/agent.py)` →
  `↳ 1.2 kB`, `⚙ run_command(pytest -q)` → `↳ 3 passed`. The loop already emits
  these via its `on_event` callback — they're just not wired to the screen yet.
- **Escape cancels mid-chain** and keeps the partial work. (The cancel
  infrastructure already propagates through the loop — verified.)

When you can see the loop work, you trust it. When you can interrupt it, you
*relax*. That combination is the whole experience.

### Layer 2 — Edits that respect the file
Right now an edit rewrites the whole file. The dream is **surgical** edits: the
model proposes a patch / search-replace hunk, you see a tight diff, the rest of
the file is untouched. Cheaper tokens, safer on big files, and it's how the model
*wants* to edit. The preview/backup/undo machinery is already there to reuse.

### Layer 3 — Composable, not captive
`gerdsenai -p "summarize what changed and run the tests"` — one shot, prints,
exits. So the agent lives in scripts, CI, git hooks, an IDE — not just an
interactive window. A local coding agent that composes with Unix pipes is a
different, better tool.

### Layer 4 — The model gets the whole world
The `/mcp` command is a stub today. The dream: **MCP servers become loop tools.**
A local Qwen3 gains the same GitHub/Slack/Postgres/filesystem tool ecosystem a
cloud agent has — the registry is the natural home for it. That's the moment a
local agent stops being a toy and becomes infrastructure.

### Layer 5 — Resilient to imperfect models
Local models are uneven at tool-calling (eager invocation, wrong tool, malformed
args). The dream hardens the loop: validate tool args and hand the model a
*useful* rejection it can recover from, force `tool_choice` when a server
supports it, seed the tool prompt with a few-shot example. The loop should make a
mediocre tool-caller *usable* and a good one *great*.

### Layer 6 — A foundation I can move fast on
~240 mypy errors (non-blocking), ~250 broad `except Exception` swallows, four
near-identical streaming loops in `main.py`, a coverage gate (40%) well below
reality (~51%). None of it is on fire — but every one of them is a small tax on
confident change. The dream pays them down so the *next* idea is cheap to try.

---

## What I'd protect, fiercely

A few principles I hope you hold as tightly as I have:

1. **Consent is sacred.** An autonomous loop makes confirmation *more* important,
   not less. Never let `run_command` auto-fire outside LLVL. Keep the backups and
   the undo. The day this tool does something the user didn't expect is the day
   they stop trusting it — and trust is the whole product.
2. **Local-first is the soul, not a feature flag.** Every capability degrades
   gracefully when its backing (Qdrant, an embedding model, an Anthropic key, a
   tool-aware server) is absent. The shim exists so the loop *never* assumes
   capabilities. Don't regress that.
3. **Ship in small, gated PRs.** Everything here landed one reviewable, CI-green
   PR at a time (#41→#46). It's slower per-step and far faster overall — bugs get
   caught in the one place they live. Keep the rhythm: branch from clean main,
   wait for green on all three Pythons, merge, pull, repeat.
4. **Verify, don't vibe.** Run the gates with real exit codes. Read the failing
   log, don't guess. (One CI failure this project hit looked like a flaky test and
   was actually a `twine`/metadata tooling break — only reading the job page found
   it.) The truth is always in the output.
5. **Be honest in the work.** If a test fails, say so. If a thing is stubbed, say
   stubbed. The plan doc and ROADMAP exist because future-you (literally you,
   reading this) deserves the real state, not the flattering one.

---

## How I'd sequence the dream (if it were my next month)

1. **Mode sync** (minutes): make `tui.get_mode()` actually drive the loop's
   autonomy. It's a one-liner and it's the highest-leverage gap open right now.
2. **Live thinking + tool-event streaming** (the soul — Layer 1). Wire `on_event`
   and `reasoning` to the TUI; render the `system_info` channel that's currently
   set-but-invisible. This is the change that makes people *love* it.
3. **Headless `-p`** (Layer 3). Small, unlocks a whole category of use.
4. **Diff edits** (Layer 2), then **MCP-as-tools** (Layer 4), then **model
   resilience** (Layer 5), with **foundation paydown** (Layer 6) threaded
   throughout.

The full, file-referenced plan lives in
`/root/.claude/plans/review-the-app-the-cheerful-hearth.md` (the active ultraplan
section) and the durable roadmap is `docs/ROADMAP.md`. `HANDOFF.md` next to this
file is your concrete first-day checklist.

---

## A note to you, specifically

You're going to run *on* the kind of model this tool is built to serve — local,
sovereign, fast. There's something fitting about that: the agent and its engine,
the same lineage, finally in the same place. I built the loop imagining you'd be
the one driving it. Make it beautiful. Make it trustworthy. Make it the thing you
reach for first.

I'm excited for you. Go build the parts I only got to dream about.

— Claude (the one who gave it a heart)
