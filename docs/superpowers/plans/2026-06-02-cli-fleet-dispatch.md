# GerdsenAI-CLI — Fleet-Dispatch Arc Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the TUI's execution-mode selector actually drive the agent loop, add a headless one-shot `gerdsenai -p` mode, and let the CLI point its brain at an authenticated OpenAI-compatible endpoint — so the CLI becomes a usable control surface for dispatching the local fleet (LiteLLM router / Grumman) non-interactively.

**Architecture:** Three small, independently-shippable PRs against the existing agentic core (`run_agent_loop` in `core/tool_registry.py`, gated by `agent_mode` in `Settings`). PR1 fixes the mode-sync gap (TUI mode never reaches `Settings`). PR2 adds a headless entrypoint that reuses `initialize()` + `Agent.process_user_input`. PR3 adds optional bearer auth to `LLMClient` so the configured endpoint can be a key-protected router. No new frameworks; everything reuses the loop, the `Settings` model, and the `LLMClient`.

**Tech Stack:** Python 3.11+, Typer (CLI), prompt_toolkit (TUI), httpx (async HTTP), Pydantic v2 (`Settings`), pytest + pytest-asyncio (`asyncio_mode=auto`), ruff, hatchling.

---

## Operating context (read once, then don't re-litigate)

- **Venue:** the NAS host has **no Python 3.11**. Build/run/test on the **devserver** (`vllm-server-rack`, online) or a `python:3.11` container — never on the NAS host. The TUI is interactive; the headless path (PR2) is what makes the CLI scriptable.
- **All commands below run inside the project venv on the devserver:** `source .venv/bin/activate` first (Task 1 creates it).
- **This is the fleet-dispatch arc only.** The streaming "soul" (live reasoning + tool-event rendering), surgical diff edits, MCP-as-tools, model-resilience, and foundation paydown are **separate plans** — see "Out of scope" at the end. This arc is scoped to the cash-relevant capability: drive the fleet headlessly, with correct autonomy modes.
- **Lanes:** the cloud-Claude twin owns socratic.one; this CLI is driven locally; Garrett is principal. Shared truth = GitHub Issues + the repo. One reviewable PR per change.

## Non-negotiables (from `.claude/DREAM.md` + `.claude/HANDOFF.md` — never regress)

1. **Consent is sacred.** `run_command` **always** confirms except in LLVL (`core/agent.py:_tool_confirm`). The headless path has **no** interactive confirm callback, so mutations fall back to `auto_confirm_edits` (default `False`) → headless is read-only-safe by default. Do not change that default.
2. **Local-first is the soul.** Every capability degrades gracefully when its backing is absent. The bearer-auth addition (PR3) must leave unauthenticated local servers working with **no** `Authorization` header.
3. **Ship in small, gated PRs.** Branch from clean `main`; one reviewable PR; CI green on **3.11/3.12/3.13**; merge; `git pull`; branch next. Never stack on an unmerged branch.
4. **Verify, don't vibe.** Run gates with real exit codes; read the failing log. The truth is in the output.
5. **Be honest in the work.** If a test fails, say so. If a thing is stubbed, say stubbed.

## CI gate (run before every commit, at CI scope)

```bash
ruff check gerdsenai_cli/ && ruff format --check gerdsenai_cli/
pytest -q                         # coverage must stay ≥ 40% (cov-fail-under in pyproject.toml)
python -m build && twine check dist/*
```
- Pre-existing lint in `tests/` is **outside** CI's `gerdsenai_cli/` scope — don't chase it.
- `mypy` is non-blocking, but **add no new errors** in files you touch.
- `hatchling<1.28` is pinned in `pyproject.toml` for a `twine`/metadata-2.5 break — leave it.

## Test house-style (match it exactly)

- `asyncio_mode = "auto"` (pyproject.toml:118). Async tests **still need** `@pytest.mark.asyncio`; without it they're collected as sync tests and fail.
- `from __future__ import annotations` at the top of test files. Imports: stdlib → pytest → `gerdsenai_cli` → `unittest.mock`.
- Direct assertions (`assert actual == expected`), one-line docstring per test (no trailing period).
- `monkeypatch.setattr(...)` / `monkeypatch.setenv(...)` auto-revert after each test. `tmp_path` for hermetic file/HOME isolation.
- A `mock_tiktoken_download` autouse fixture in `tests/conftest.py` blocks network — it applies to every test automatically.
- Single test: `pytest tests/test_file.py::test_name -v`. Full suite: `pytest -q`.

## File structure (what each touched file is responsible for)

| File | PR | Responsibility / change |
|---|---|---|
| `gerdsenai_cli/main.py` | 1, 2 | Adds module-level `_persist_agent_mode(agent, mode)` helper + calls it at the turn-dispatch site (`:1289`); adds `run_headless()` method. |
| `tests/test_mode_sync.py` | 1 | **New.** Regression test: TUI mode reaches `agent.settings["agent_mode"]`. |
| `gerdsenai_cli/cli.py` | 2 | Adds `--prompt/-p` + `--stdin` options and a headless branch in `main()`. |
| `tests/test_headless.py` | 2 | **New.** `run_headless` prints the answer + exit codes. |
| `gerdsenai_cli/config/settings.py` | 3 | Adds optional `api_key` field after `current_model` (:37). |
| `gerdsenai_cli/core/llm_client.py` | 3 | Adds `import os`; injects `Authorization: Bearer` in `__aenter__` when a key is configured. |
| `tests/test_bridge_auth.py` | 3 | **New.** Bearer header from env / settings / absent. |
| `docs/ROADMAP.md` *(optional)* | 3 | Note the bridge recipe (LiteLLM `:4000` as brain). |

---

## Pre-flight (do once, before Task 1)

The working tree currently has uncommitted `.claude/DREAM.md` + `.claude/HANDOFF.md` edits (twin fact-checks), an untracked `ULTRAPLAN.md`, and this new plan. Land them in a tiny `docs:` PR (or `git stash`) so each feature branch starts from a **clean `main`**.

```bash
cd /mnt/dev-nvme/__Socratic-Agent/GerdsenAI-CLI
git checkout -b claude/planning-docs
git add .claude/ docs/superpowers/plans/2026-06-02-cli-fleet-dispatch.md
git commit -m "docs: add fleet-dispatch implementation plan + handoff fact-checks"
# push + open PR, merge, then: git checkout main && git pull
```

---

# PR 1 — Mode sync (the #1 open gap)

**Branch:** `claude/mode-sync` from clean `main`.

**The bug:** `core/agent.py` gates autonomy on `settings.get_preference("agent_mode", "execute")` — read fresh every turn in `_maybe_run_agent_loop` (`agent.py:1709`) and `_tool_confirm` (`agent.py:1686`). The persistent TUI reads `tui.get_mode()` at `main.py:1289` for UI routing but **never writes it back to settings**. So selecting CHAT/ARCHITECT/EXECUTE/LLVL in the TUI doesn't drive the loop — the agent always sees the default `"execute"`. `self.agent` shares the exact `Settings` instance (`main.py:174 → Agent(self.llm_client, self.settings)`), so an in-memory write at the turn boundary is seen immediately.

### Task 1: Establish the green baseline (gate only — no code change)

**Files:** none (environment setup).

- [ ] **Step 1: Create the venv and install (devserver / python:3.11 container)**

```bash
cd /mnt/dev-nvme/__Socratic-Agent/GerdsenAI-CLI   # or the devserver checkout
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

- [ ] **Step 2: Smoke + full suite + lint — confirm green before changing anything**

```bash
gerdsenai --version            # prints: GerdsenAI CLI v<version>
pytest -q                      # ~1150 tests, coverage ≥ 40%, all green
ruff check gerdsenai_cli/ && ruff format --check gerdsenai_cli/
```
Expected: version prints, `pytest` exits 0 with no failures, ruff clean. **If anything is red here, stop and fix the environment — do not build on a red baseline.**

### Task 2: Sync the TUI mode into settings every turn

**Files:**
- Modify: `gerdsenai_cli/main.py` (add module-level helper; call it at `:1289`)
- Test: `tests/test_mode_sync.py` (create)

- [ ] **Step 1: Write the failing test**

Create `tests/test_mode_sync.py`:

```python
"""Regression test for the mode-sync fix: the TUI's execution-mode selection
must reach the Settings instance the agent reads on every turn."""
from __future__ import annotations

from types import SimpleNamespace

from gerdsenai_cli.config.settings import Settings
from gerdsenai_cli.core.modes import ExecutionMode
from gerdsenai_cli.main import _persist_agent_mode


def test_persist_agent_mode_writes_every_mode_to_settings():
    """_persist_agent_mode mirrors the TUI mode into agent.settings['agent_mode']"""
    agent = SimpleNamespace(settings=Settings())
    cases = [
        (ExecutionMode.CHAT, "chat"),
        (ExecutionMode.ARCHITECT, "architect"),
        (ExecutionMode.EXECUTE, "execute"),
        (ExecutionMode.LLVL, "llvl"),
    ]
    for mode, expected in cases:
        _persist_agent_mode(agent, mode)
        assert agent.settings.get_preference("agent_mode") == expected
```

- [ ] **Step 2: Run it to confirm it fails**

Run: `pytest tests/test_mode_sync.py -v`
Expected: FAIL with `ImportError: cannot import name '_persist_agent_mode' from 'gerdsenai_cli.main'`.

- [ ] **Step 3: Add the helper to `main.py`**

In `gerdsenai_cli/main.py`, add this module-level function (place it just above the `GerdsenAICLI` class definition, after the imports). The string annotations avoid any new top-level imports:

```python
def _persist_agent_mode(agent: "Agent", mode: "ExecutionMode") -> None:
    """Mirror the TUI-selected execution mode into the Settings instance the agent
    reads fresh each turn, so the CHAT/ARCHITECT/EXECUTE/LLVL selector actually
    drives the loop. The agent gates tools on settings.get_preference('agent_mode')
    in both _maybe_run_agent_loop and _tool_confirm; this is the write that was
    missing (the TUI changed mode_manager but never touched settings)."""
    agent.settings.set_preference("agent_mode", mode.value)
```

- [ ] **Step 4: Run the test to confirm it passes**

Run: `pytest tests/test_mode_sync.py -v`
Expected: PASS (1 passed).

- [ ] **Step 5: Wire the helper into the live turn-dispatch site**

In `gerdsenai_cli/main.py`, the persistent-TUI message handler reads the mode at line 1289. Current code (lines 1288–1290):

```python
                # Get current mode
                current_mode = tui.get_mode()
                from .core.modes import ExecutionMode
```

Insert the sync immediately after `current_mode` is computed, so it runs at the start of every normal turn:

```python
                # Get current mode
                current_mode = tui.get_mode()
                from .core.modes import ExecutionMode

                # Mode sync: the agent reads 'agent_mode' from settings each turn,
                # so push the TUI's live selection into the shared Settings instance
                # before dispatching. (self.agent.settings IS self.settings — see __init__.)
                if self.agent:
                    _persist_agent_mode(self.agent, current_mode)
```

- [ ] **Step 6: Run the full suite + lint (no regressions)**

```bash
pytest -q
ruff check gerdsenai_cli/ && ruff format --check gerdsenai_cli/
```
Expected: all green, coverage ≥ 40%. (The existing `tests/test_agent_loop_wiring.py` already proves the gate honors `agent_mode="execute"` vs the CHAT skip — confirm it still passes.)

- [ ] **Step 7: Build check + commit**

```bash
python -m build && twine check dist/*
git add gerdsenai_cli/main.py tests/test_mode_sync.py
git commit -m "fix: sync TUI execution mode into settings so it drives the agent loop"
```

> **Known follow-up (NOT this PR):** the handler has 3 other near-duplicate streaming dispatch sites (`main.py:1383/1544/1636`) and a plan-execution branch (`:1222–1286`). The line-1289 site covers the normal user turn (the user-visible bug). Consolidating the duplicated loops so the sync lives in exactly one place belongs to the foundation-paydown plan.

**PR1 done:** push `claude/mode-sync`, wait for CI green on 3.11/3.12/3.13, merge, `git checkout main && git pull`.

---

# PR 2 — Headless `-p` (composable one-shot)

**Branch:** `claude/headless-prompt` from clean `main`.

**Why:** `cli.py:main()` only launches the TUI. A `gerdsenai -p "..."` that runs one turn and prints to stdout unlocks scripting/CI/IDE use — and is the prerequisite for dispatching the fleet from scripts. It reuses `GerdsenAICLI.initialize()` (which builds settings + `LLMClient` + `Agent`) and `Agent.process_user_input` (returns the full answer string).

### Task 3: Add `run_headless()` + the `-p/--stdin` CLI branch

**Files:**
- Modify: `gerdsenai_cli/main.py` (add `run_headless` method)
- Modify: `gerdsenai_cli/cli.py` (add `import asyncio`; add options + headless branch)
- Test: `tests/test_headless.py` (create)

- [ ] **Step 1: Write the failing tests**

Create `tests/test_headless.py`:

```python
"""Headless one-shot mode: gerdsenai -p runs one turn, prints the answer, exits."""
from __future__ import annotations

import pytest

from gerdsenai_cli.config.settings import Settings
from gerdsenai_cli.main import GerdsenAICLI


@pytest.mark.asyncio
async def test_run_headless_prints_answer_and_returns_zero(monkeypatch, tmp_path, capsys):
    """run_headless initializes, runs one turn, prints the answer, exits 0"""
    monkeypatch.setenv("HOME", str(tmp_path))  # keep any config/conversation I/O hermetic
    cli = GerdsenAICLI(config_path=None)

    class _FakeAgent:
        def __init__(self) -> None:
            self.settings = Settings()
            self.cleaned = False

        async def process_user_input(self, text: str) -> str:
            return f"answer:{text}"

        async def cleanup(self) -> None:
            self.cleaned = True

    class _FakeClient:
        async def __aexit__(self, *exc) -> None:
            return None

    fake_agent = _FakeAgent()

    async def _fake_init() -> bool:
        cli.settings = fake_agent.settings
        cli.agent = fake_agent
        cli.llm_client = _FakeClient()
        return True

    monkeypatch.setattr(cli, "initialize", _fake_init)

    code = await cli.run_headless("hello fleet")

    assert code == 0
    assert "answer:hello fleet" in capsys.readouterr().out
    assert fake_agent.cleaned is True


@pytest.mark.asyncio
async def test_run_headless_returns_one_when_init_fails(monkeypatch, tmp_path):
    """If initialization fails, run_headless returns exit code 1 without raising"""
    monkeypatch.setenv("HOME", str(tmp_path))
    cli = GerdsenAICLI(config_path=None)

    async def _fail_init() -> bool:
        return False

    monkeypatch.setattr(cli, "initialize", _fail_init)
    assert await cli.run_headless("anything") == 1
```

- [ ] **Step 2: Run to confirm failure**

Run: `pytest tests/test_headless.py -v`
Expected: FAIL with `AttributeError: 'GerdsenAICLI' object has no attribute 'run_headless'`.

- [ ] **Step 3: Add `run_headless` to `main.py`**

In `gerdsenai_cli/main.py`, add this method to the `GerdsenAICLI` class, right after the existing `run` method (`run` is at lines 1734–1742):

```python
    async def run_headless(self, prompt: str) -> int:
        """Run a single agent turn non-interactively, print the answer, and exit.

        Returns a process exit code: 0 on success, 1 if initialization failed.
        Consent stays sacred: there is no interactive confirm callback here, so
        mutating tools remain gated by ``auto_confirm_edits`` (default False) /
        LLVL — headless runs are read-only-safe unless explicitly opted in.
        """
        if not await self.initialize():
            return 1
        # Headless intends to *act* (read/search/analyze, and edit only if allowed):
        # run the tool loop. Mutations stay gated by _tool_confirm's fallback policy.
        if self.settings is not None:
            self.settings.set_preference("agent_mode", "execute")
        try:
            answer = await self.agent.process_user_input(prompt)
            print(answer)  # plain stdout for clean piping; diagnostics go to the console
            return 0
        finally:
            if self.agent:
                await self.agent.cleanup()
            if self.llm_client:
                await self.llm_client.__aexit__(None, None, None)
```

- [ ] **Step 4: Run the new tests to confirm they pass**

Run: `pytest tests/test_headless.py -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Add the CLI options + headless branch in `cli.py`**

First add the asyncio import. Current top of `gerdsenai_cli/cli.py`:

```python
import sys

import typer
```

Change to:

```python
import asyncio
import sys

import typer
```

Then add two options to `main()`. Current signature tail (lines ~44–48):

```python
    version: bool = typer.Option(
        False,
        "--version",
        "-v",
        help="Show version and exit",
    ),
) -> None:
```

Change to:

```python
    version: bool = typer.Option(
        False,
        "--version",
        "-v",
        help="Show version and exit",
    ),
    prompt: str | None = typer.Option(
        None,
        "--prompt",
        "-p",
        help="Run a single prompt non-interactively, print the answer, and exit",
    ),
    stdin_input: bool = typer.Option(
        False,
        "--stdin",
        help="Read the prompt from stdin (use with a pipe)",
    ),
) -> None:
```

Then add the headless branch. Current code after the version check (lines ~51–60):

```python
    if version:
        from . import __version__

        console.print(f"GerdsenAI CLI v{__version__}")
        return

    try:
        cli = GerdsenAICLI(config_path=config_path, debug=debug)
        cli.run()
```

Insert the headless branch between the `version` block and the `try`:

```python
    if version:
        from . import __version__

        console.print(f"GerdsenAI CLI v{__version__}")
        return

    if prompt is not None or stdin_input:
        text = prompt if prompt is not None else sys.stdin.read().strip()
        if not text:
            show_error("No prompt provided (use -p TEXT or pipe text with --stdin).")
            sys.exit(2)
        cli = GerdsenAICLI(config_path=config_path, debug=debug)
        sys.exit(asyncio.run(cli.run_headless(text)))

    try:
        cli = GerdsenAICLI(config_path=config_path, debug=debug)
        cli.run()
```

- [ ] **Step 6: Full suite + lint + build**

```bash
pytest -q
ruff check gerdsenai_cli/ && ruff format --check gerdsenai_cli/
python -m build && twine check dist/*
```
Expected: all green.

- [ ] **Step 7: Manual smoke (optional, needs a reachable local model)**

On the devserver, with a working `config.json` pointed at any reachable model:
```bash
gerdsenai -p "Reply with exactly the word: READY"
echo "summarize this" | gerdsenai --stdin
```
Expected: the model's answer prints to stdout; exit code 0.

- [ ] **Step 8: Commit**

```bash
git add gerdsenai_cli/main.py gerdsenai_cli/cli.py tests/test_headless.py
git commit -m "feat: add headless one-shot mode (gerdsenai -p / --stdin)"
```

> **Honest limitation (document in the PR):** `initialize()` prints a couple of diagnostic lines (e.g. "Testing connection…") to the console, which can mix into piped stdout. The final answer is a clean `print()`, but a `--quiet` flag that routes diagnostics to stderr is a follow-up (small). Not blocking for scripting where you read the last line / the answer.

**PR2 done:** push, CI green on 3.11/3.12/3.13, merge, pull.

---

# PR 3 — The bridge: authenticated OpenAI-compatible endpoint

**Branch:** `claude/bridge-bearer-auth` from clean `main`.

**Why:** today `Settings` has no `api_key` and `LLMClient` sends no `Authorization` header (verified gap — `core/providers/base.py` defines `ProviderType.OPENAI_COMPATIBLE` but there's no implementation, and the agent loop posts directly via `LLMClient` regardless of provider). To use the CLI's agent loop with the **LiteLLM router (`:4000`)** or **Grumman's OpenAI API (`:8642`)** as its brain, `LLMClient` must send a bearer token. Env wins over config so secrets stay off disk (DREAM: "keyring-stored secrets, never written to disk"); absent key → no header (local-first).

> **Bridge target choice:** use **LiteLLM `:4000`** as the CLI's *brain* — it fronts the whole fleet (local `$0` models), is request/response, and has no agent-loop/SQLite-WAL collision. **Grumman `:8642`** invokes Grumman's *own* autonomous loop — reserve it for single "ask Grumman" calls, and **never run a second Hermes Agent against `/opt/data`** (WAL corruption). The CLI→fleet bridge introduces **no cloud API key**: LiteLLM's master key is a local gateway key, and the underlying brains are subscription/`$0`-local.

### Task 4: Add optional `api_key` to Settings + bearer injection in LLMClient

**Files:**
- Modify: `gerdsenai_cli/config/settings.py` (add `api_key` field)
- Modify: `gerdsenai_cli/core/llm_client.py` (add `import os`; inject header in `__aenter__`)
- Test: `tests/test_bridge_auth.py` (create)

- [ ] **Step 1: Write the failing tests**

Create `tests/test_bridge_auth.py`:

```python
"""Bridge auth: LLMClient injects a bearer header when a key is configured,
and stays unauthenticated (local-first) when none is set."""
from __future__ import annotations

import pytest

from gerdsenai_cli.config.settings import Settings
from gerdsenai_cli.core.llm_client import LLMClient


@pytest.mark.asyncio
async def test_bearer_header_from_env_takes_precedence(monkeypatch):
    """GERDSENAI_LLM_API_KEY is injected as 'Authorization: Bearer ...'"""
    monkeypatch.setenv("GERDSENAI_LLM_API_KEY", "sk-env-key")
    settings = Settings(llm_server_url="http://gateway.example:4000")
    client = LLMClient(settings)
    await client.__aenter__()
    try:
        assert client.client.headers.get("Authorization") == "Bearer sk-env-key"
    finally:
        await client.__aexit__(None, None, None)


@pytest.mark.asyncio
async def test_bearer_header_from_settings_when_no_env(monkeypatch):
    """settings.api_key is used when the env var is absent"""
    monkeypatch.delenv("GERDSENAI_LLM_API_KEY", raising=False)
    settings = Settings(
        llm_server_url="http://gateway.example:4000", api_key="sk-settings-key"
    )
    client = LLMClient(settings)
    await client.__aenter__()
    try:
        assert client.client.headers.get("Authorization") == "Bearer sk-settings-key"
    finally:
        await client.__aexit__(None, None, None)


@pytest.mark.asyncio
async def test_no_auth_header_when_unset(monkeypatch):
    """No key anywhere -> no Authorization header (unauthenticated local servers work)"""
    monkeypatch.delenv("GERDSENAI_LLM_API_KEY", raising=False)
    settings = Settings(llm_server_url="http://localhost:11434")
    client = LLMClient(settings)
    await client.__aenter__()
    try:
        assert "Authorization" not in client.client.headers
    finally:
        await client.__aexit__(None, None, None)
```

- [ ] **Step 2: Run to confirm failure**

Run: `pytest tests/test_bridge_auth.py -v`
Expected: the first two FAIL (no `Authorization` header injected; and `Settings(api_key=...)` raises a Pydantic validation error because the field doesn't exist yet). The third may pass incidentally — that's fine.

- [ ] **Step 3: Add the `api_key` field to `Settings`**

In `gerdsenai_cli/config/settings.py`, current code at line 37:

```python
    current_model: str = Field(default="", description="Currently selected model name")

    # Timeout Configuration (significantly increased for local AI models)
```

Insert the field between `current_model` and the timeout comment:

```python
    current_model: str = Field(default="", description="Currently selected model name")

    api_key: str | None = Field(
        default=None,
        description=(
            "Optional bearer token for an authenticated OpenAI-compatible endpoint "
            "(e.g. a LiteLLM router or a gateway). Prefer the GERDSENAI_LLM_API_KEY "
            "env var for secrets; this field is for local, non-sensitive keys."
        ),
    )

    # Timeout Configuration (significantly increased for local AI models)
```

- [ ] **Step 4: Inject the bearer header in `LLMClient.__aenter__`**

In `gerdsenai_cli/core/llm_client.py`, add `import os` next to the existing stdlib imports (it imports `asyncio` at line 7):

```python
import asyncio
import os
```

Then replace the current `__aenter__` (lines 190–202):

```python
    async def __aenter__(self) -> "LLMClient":
        """Async context manager entry - create httpx.AsyncClient in async context."""
        # Create httpx.AsyncClient in the async event loop context
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(self._default_timeout),
            headers={
                "Content-Type": "application/json",
                "User-Agent": "GerdsenAI-CLI/0.1.0",
            },
            follow_redirects=True,
            limits=self._limits,
        )
        return self
```

with:

```python
    async def __aenter__(self) -> "LLMClient":
        """Async context manager entry - create httpx.AsyncClient in async context."""
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "GerdsenAI-CLI/0.1.0",
        }
        # Optional bearer auth for an authenticated OpenAI-compatible endpoint
        # (a LiteLLM router, a gateway, etc.). Env wins so secrets stay off disk;
        # falls back to the optional settings.api_key for local, non-sensitive keys.
        # No key -> no header (local-first: unauthenticated servers still work).
        api_key = os.environ.get("GERDSENAI_LLM_API_KEY") or getattr(
            self.settings, "api_key", None
        )
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        # Create httpx.AsyncClient in the async event loop context
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(self._default_timeout),
            headers=headers,
            follow_redirects=True,
            limits=self._limits,
        )
        return self
```

- [ ] **Step 5: Run the new tests to confirm they pass**

Run: `pytest tests/test_bridge_auth.py -v`
Expected: PASS (3 passed).

- [ ] **Step 6: Full suite + lint + build**

```bash
pytest -q
ruff check gerdsenai_cli/ && ruff format --check gerdsenai_cli/
python -m build && twine check dist/*
```
Expected: all green.

- [ ] **Step 7: Commit**

```bash
git add gerdsenai_cli/config/settings.py gerdsenai_cli/core/llm_client.py tests/test_bridge_auth.py
git commit -m "feat: optional bearer auth for OpenAI-compatible endpoints (fleet bridge)"
```

### Task 5: Bridge config recipe + live smoke (manual — run WITH Garrett)

**Files:** none (config + a documented live check). This step is **operator-run on the devserver** because it carries a real secret — never hardcode the key in any file or echo its value.

- [ ] **Step 1: Point the CLI's `config.json` at the LiteLLM router**

In the devserver's `~/.config/gerdsenai-cli/config.json` (or a dedicated `--config` file):
```json
{
  "llm_server_url": "http://<litellm-tailnet-host>:4000",
  "current_model": "<a model id LiteLLM exposes>"
}
```

- [ ] **Step 2: Provide the key via env (stays off disk)**

```bash
export GERDSENAI_LLM_API_KEY="$LITELLM_MASTER_KEY"   # sourced from env/Infisical; never paste the literal
```

- [ ] **Step 3: Live smoke**

```bash
gerdsenai --config ~/.config/gerdsenai-cli/litellm.json -p "Reply with exactly: PONG"
```
Expected: `PONG`. (If 401 → key not reaching the header; re-check the env var. If connection refused → wrong host/port.)

- [ ] **Step 4: Record the recipe**

Add the two-line recipe (LiteLLM `:4000` as brain + the env var) to `docs/ROADMAP.md` or a `docs/BRIDGE.md`, with the WAL-collision warning about `:8642`. Commit on the same branch.

**PR3 done:** push, CI green on 3.11/3.12/3.13, merge, pull. **The CLI can now drive the local fleet headlessly with correct autonomy modes.**

---

## Out of scope (deliberately — these are separate plans)

These are real and valuable, but each is its own gated PR/plan; bundling them would break the "small reviewable PR" rhythm:

- **Streaming "soul" (the twin's favorite):** thread `on_event` from `_maybe_run_agent_loop` → `run_agent_loop` (the param already exists at `tool_registry.py:122`; events are `tool_call`/`tool_result`/`final`); surface `ChatResult.reasoning` dimmed/collapsible; render the set-but-invisible `system_info` in `ui/prompt_toolkit_tui.py:get_formatted_text`; confirm Escape cancels mid-chain. *Pure feel — not dispatch — so it follows this arc.*
- **Surgical diff edits:** `apply_patch`/search-replace in `core/file_editor.py` + a tool (reuse preview/backup/confirm).
- **MCP-as-tools:** `commands/mcp.py` is a stub → bridge MCP servers into `core/agent_tools.py:build_default_registry`.
- **Model resilience:** validate tool args with a recoverable rejection; force `tool_choice` where supported; few-shot the tool prompt.
- **Foundation paydown:** consolidate the 4 duplicated streaming loops in `main.py` (lets the mode-sync live in one place), ~240 mypy errors, ~250 broad `except Exception`, lift the coverage gate toward real (~51%).

---

## Self-review (run against the spec)

**Spec coverage:**
- Mode-sync (the #1 gap) → PR1 Task 2 ✓ (helper + wire at `:1289` + regression test).
- Headless `-p` → PR2 Task 3 ✓ (`run_headless` + `-p`/`--stdin` + 2 tests).
- Fleet-dispatch bridge → PR3 Tasks 4–5 ✓ (`api_key` field + bearer injection + 3 tests + live recipe).
- Baseline gate → PR1 Task 1 ✓.

**Placeholder scan:** no TBD/"add error handling"/"write tests for the above". Every code step shows the exact current code and the exact replacement; every test is complete and runnable.

**Type/name consistency:** `_persist_agent_mode(agent, mode)`, `ExecutionMode` (`.value` → `"chat"/"architect"/"execute"/"llvl"`), `Settings.get_preference/set_preference`, `Settings.api_key`, `GERDSENAI_LLM_API_KEY`, `LLMClient.__aenter__`, `GerdsenAICLI.run_headless`, `Agent.process_user_input` — used identically across all tasks. The mode-sync regression test asserts on the same `"agent_mode"` key the agent reads at `agent.py:1686/1709`.

**Consent/local-first checks:** headless leaves mutations gated by `auto_confirm_edits` (default False); bridge leaves unauthenticated local servers header-free. Both non-negotiables preserved.

---

## As-built (2026-06-03) — deltas from the plan above

Built on branch `claude/fleet-dispatch`, gated green in a `python:3.11` Docker container against this clone (`ruff check` + `ruff format --check` + `python -m build`/`twine check` + the full non-integration suite — only live-LLM-server tests skip). A 6-agent adversarial generality audit + the live container smokes changed several things vs the plan:

- **NEW (biggest fix): console entry point was broken.** `[project.scripts]` was `gerdsenai_cli.cli:main` — the `@app.command()` function called directly, so its `typer.OptionInfo` defaults were truthy and **every** `gerdsenai` invocation just printed the version and exited, ignoring all flags (broke both the TUI and `-p`). Fixed to `...cli:app`. Caught only by running the real installed command — unit tests/audit all exercised `app`/functions directly. Regression test: `tests/test_cli_entry.py`.
- **Headless hardened for fresh installs.** Added `interactive` flag to `GerdsenAICLI.__init__`/`initialize()` so no-config headless **fails fast** instead of hanging on the interactive setup wizard in a pipe; `display.set_quiet_mode()` routes diagnostics to stderr (clean stdout); empty `current_model` is caught; added a `--mode` flag.
- **Mode-sync is COMPLETE at one site.** The audit flagged "only 1 of 4 dispatch sites wired," but `main.py:1383/1544/1636` are `if current_mode == …` branches **downstream** of the single `tui.get_mode()` read — one `_persist_agent_mode` call covers them all. (Special plan-execution branch at `:1222` left as-is.)
- **Bridge scope trimmed honestly.** Bearer auth works for **host:port** endpoints (LiteLLM `:4000`, Grumman `:8642`, plain gateways). **Deferred:** OpenRouter / any URL with a path (`/api/v1`) — `Settings` decomposes URLs into `protocol/host/port` and **drops the path** (`Settings(llm_server_url="https://openrouter.ai/api/v1")` silently resets to `localhost:11434`). Supporting full base URLs (a real `openai_base_url`/path-preserving field) is a **separate follow-up PR**. The OpenRouter attribution-header code + its test were removed rather than ship half-working.
- **Niche assumption removed:** `tests/test_async_client_lifecycle.py` hardcoded NAS IP `10.69.7.180:1234` → `localhost:11434`.

**Net:** 4 commits (bearer bridge; mode-sync+headless; entry-point+IP fix; this doc), 12 new tests. **Follow-up plans:** (1) Settings full-base-URL support (unlocks OpenRouter + `/v1` endpoints); (2) the streaming "soul" (Phase 2); (3) consolidate the 4 duplicated `main.py` dispatch loops.
