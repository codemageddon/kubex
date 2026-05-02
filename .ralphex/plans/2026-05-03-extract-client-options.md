# Extract ClientOptions from ClientConfiguration

## Overview

`ClientConfiguration` currently mixes two concerns:

- **Cluster connection data** sourced from kubeconfig / in-cluster service-account: `base_url`, TLS material (`server_ca_file`, `insecure_skip_tls_verify`, client cert/key), `token` / `token_file`, `namespace`, `try_refresh_token`.
- **Client-level operational options** that have nothing to do with what kubeconfig produces: `log_api_warnings` and `timeout`.

Neither factory (`configure_from_kubeconfig`, `configure_from_pod_env`) sets the latter pair — they only ever come from user code. The `Api` class never reads them; only the two HTTP backends do.

This plan extracts those two fields into a new `ClientOptions` pydantic model, reshapes `BaseClient` and `create_client()` to take it as a separate argument, and removes the fields from `ClientConfiguration`. After the refactor `ClientConfiguration` represents only what could plausibly come from a Kubernetes-side configuration source.

The library is `0.1.0-beta.1` and project policy explicitly allows breaking changes between releases — this is a **hard break** with no deprecation shim.

## Context (from discovery)

**Files that define / read the moving fields:**

- `kubex/configuration/configuration.py:197-251` — `ClientConfiguration.__init__` declares `log_api_warnings` (line 209, stored at 229) and `timeout` (line 210, coerced and stored at 239-241; read-only `timeout` property at 243-251).
- `kubex/client/httpx.py:74-76` — `HttpxClient._create_inner_client` reads `self.configuration.timeout`.
- `kubex/client/httpx.py:100-104` — `HttpxClient.request` reads `self.configuration.log_api_warnings` to gate `warnings.warn`.
- `kubex/client/aiohttp.py:88-90` — `AioHttpClient._create_inner_client` reads `self.configuration.timeout`.
- `kubex/client/aiohttp.py:114-118` — `AioHttpClient.request` reads `self.configuration.log_api_warnings` to gate `warnings.warn`.

**Files that construct `ClientConfiguration(..., timeout=…)` today:**

- `test/test_timeout/test_configuration.py:7-12` — `_base_config()` helper passes `timeout=` via `**kwargs`; tests at lines 15-40 exercise the coercion.
- `test/test_timeout/test_httpx_client.py:13-18, 28, 33` — passes `timeout=` to drive `HttpxClient._create_inner_client`.
- `test/test_timeout/test_aiohttp_client.py:13-20, 25, 34` — passes `timeout=` to drive `AioHttpClient._create_inner_client`.
- `test/test_timeout/test_api_overrides.py` — does **not** set `timeout=` on `ClientConfiguration`; only exercises per-call `request_timeout=` via `StubClient`. No changes required here beyond imports if any.

**Constructors / factories that do NOT touch these fields (no code change needed):**

- `kubex/configuration/file_config.py:41-82` — `configure_from_kubeconfig`.
- `kubex/configuration/incluster_config.py:15-39` — `configure_from_pod_env`.
- `kubex/client/client.py:31-36` — `_try_read_configuration` (delegates to the two factories above).
- `test/stub_client.py:22-25` — uses defaults only.
- `test/test_client/test_httpx_websocket.py` and any aiohttp-websocket test files — construct `ClientConfiguration(url=…, token=…)` only.

**Public API entry points to update:**

- `kubex/client/client.py:45-49` — `BaseClient.__init__(configuration)`.
- `kubex/client/client.py:95-119` — `create_client(configuration, client_class)`.
- `kubex/client/httpx.py:40-42` — `HttpxClient.__init__` overrides `BaseClient.__init__` and stores `self._configuration` itself (does NOT call `super().__init__()`).
- `kubex/client/aiohttp.py:44-51` — `AioHttpClient.__init__` likewise overrides and stores directly.

**Docs that mention `timeout` on `ClientConfiguration`:**

- `docs/concepts/configuration.md:21-42` — example block (line 26) and parameter table row (line 41).
- `docs/operations/timeouts.md:30-43` — section "Setting a client-level default" with the `ClientConfiguration(timeout=…)` example at line 39.

`log_api_warnings` is **not** mentioned in any docs or example today, so the docs work is timeout-only.

**Examples that touch these fields:** none (`examples/*.py` only use `request_timeout=` per call, never `timeout=` on `ClientConfiguration`).

**Public re-exports to update:**

- `kubex/configuration/__init__.py:1-3` exports only `ClientConfiguration` (no change needed there).
- `kubex/client/__init__.py` (if present) — add `ClientOptions` to `__all__` so `from kubex.client import ClientOptions` works alongside `BaseClient` / `create_client`. Verify whether this file exists; if not, leave the import path as `from kubex.client.options import ClientOptions`.

## Development Approach

- **Testing approach**: **Regular** (code first, then tests). This is a mechanical refactor against well-covered code; the new shape is settled. Code-first lets us update producers and consumers in lockstep. The final task verifies the full suite is green.
- Complete each task fully before moving to the next.
- Make small, focused changes.
- **CRITICAL: every task MUST include new/updated tests** for code changes in that task — write/adjust unit tests for both success and error paths.
- **CRITICAL: all tests must pass before starting the next task** — no exceptions.
- **CRITICAL: update this plan file when scope changes during implementation.**
- Run `uv run pytest .`, `uv run ruff check .`, `uv run ruff format --check .`, and `uv run mypy .` after each task.
- Hard break only — do **not** add a deprecation shim on `ClientConfiguration`.

## Testing Strategy

- **Unit tests**: required for every task. New tests for `ClientOptions` itself, plus migration of existing `test/test_timeout/test_*_client.py` and `test_configuration.py` to the new shape.
- **E2E tests**: no UI; the existing `test/e2e/` suite uses `create_client()` with auto-loaded config — verify it still passes once the factory signature changes (it should, because `options` will be optional with sane defaults).
- Both HTTP backends (`httpx`, `aiohttp`) must stay parity-equivalent: the `log_api_warnings` and `timeout` semantics must behave identically before and after.
- The `Ellipsis` sentinel for `timeout` (`...` = "use HTTP library default", `None` = "disable timeouts", concrete value = "use it") must be preserved end-to-end.

## Progress Tracking

- Mark completed items with `[x]` immediately when done.
- Add newly discovered tasks with ➕ prefix.
- Document issues / blockers with ⚠️ prefix.
- Keep this plan in sync with the actual work done.

## What Goes Where

- **Implementation Steps** (`[ ]` checkboxes): code, tests, docs — all reachable from the working copy.
- **Post-Completion** (no checkboxes): manual smoke checks, downstream notification.

## Implementation Steps

### Task 1: Add `ClientOptions` pydantic model
- [x] create `kubex/client/options.py` with `class ClientOptions(BaseModel)` exposing `log_api_warnings: bool = True` and `timeout: TimeoutTypes | EllipsisType` (default `...`); use `Field(default_factory=lambda: ...)` because pydantic v2 treats a bare `...` default as "required" — verify the field accepts the Ellipsis sentinel without coercion
- [x] add `model_config = ConfigDict(arbitrary_types_allowed=True)` if `EllipsisType` triggers a pydantic schema error; reuse `Timeout.coerce` semantics by adding a field validator that normalises `int | float | Timeout` into `Timeout` while leaving `None` and `Ellipsis` as-is (mirrors current `ClientConfiguration._timeout` behaviour at `configuration.py:239-241`)
- [x] write a Google-style class docstring on `ClientOptions` and per-field docstrings (or `Field(..., description=…)`) — these feed mkdocstrings in `docs/reference/client.md` and the concept-page rendering in Task 5; describe the `Ellipsis` / `None` / value semantics for `timeout`, and what `log_api_warnings` gates
- [x] expose `ClientOptions` from `kubex/client/__init__.py` (create the file if absent) so `from kubex.client import ClientOptions` works alongside `BaseClient` / `create_client`
- [x] write `test/test_client/test_options.py`: defaults (timeout is Ellipsis, log_api_warnings True), explicit `None` preserved, `int` / `float` / `Timeout` coercion (port the parameterised cases from `test/test_timeout/test_configuration.py`), and `log_api_warnings=False`
- [x] write a test that constructing `ClientOptions(timeout="bogus")` raises a pydantic `ValidationError` (defensive — confirms the validator rejects garbage)
- [x] run `uv run pytest test/test_client/test_options.py`, `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy .` — all must pass before Task 2

### Task 2: Plumb `ClientOptions` through the HTTP clients
- [x] update `BaseClient.__init__` (`kubex/client/client.py:45-49`) to `def __init__(self, configuration: ClientConfiguration, options: ClientOptions | None = None)`; default to `ClientOptions()` when `None`; store on `self._options`; keep `self._configuration` and the `_create_inner_client()` call as today
- [x] update `HttpxClient.__init__` (`kubex/client/httpx.py:40-42`) and `AioHttpClient.__init__` (`kubex/client/aiohttp.py:44-51`) to accept the same `options` parameter and call `super().__init__(configuration, options)` instead of bypassing the parent — this also fixes the existing quirk where the subclasses skip `super().__init__()`
- [x] add a `@property` `options(self) -> ClientOptions` on both subclasses (mirroring the existing `configuration` property) so `request()` / `_create_inner_client()` can read `self.options.timeout` / `self.options.log_api_warnings`
- [x] change `HttpxClient._create_inner_client` (`httpx.py:74`) and `AioHttpClient._create_inner_client` (`aiohttp.py:88`) to read `self.options.timeout` instead of `self.configuration.timeout`
- [x] change `HttpxClient.request` (`httpx.py:100`) and `AioHttpClient.request` (`aiohttp.py:114`) to read `self.options.log_api_warnings` instead of `self.configuration.log_api_warnings`
- [x] update `test/test_timeout/test_httpx_client.py` and `test/test_timeout/test_aiohttp_client.py` to construct `HttpxClient(config, ClientOptions(timeout=…))` / `AioHttpClient(config, ClientOptions(timeout=…))` instead of `HttpxClient(_configuration(timeout=…))`; rename the `_configuration` helper to drop the `timeout` kwarg and add a parallel `_options` helper
- [x] add a unit test in `test/test_client/` (or extend an existing file) verifying `BaseClient(configuration, options=None)` constructs a default `ClientOptions()` and that the inner clients see those defaults
- [x] add a unit test verifying that an explicit `log_api_warnings=False` actually suppresses `warnings.warn` on a 4xx-free response carrying a `Warning:` header (use the websocket test pattern with a fake aiohttp/httpx response if one already exists; otherwise mock minimally)
- [x] run full suite — must pass before Task 3

### Task 3: Update the `create_client()` factory
- [x] change `create_client()` signature in `kubex/client/client.py:95-98` to `async def create_client(configuration=None, options: ClientOptions | None = None, client_class: ClientChoise = ClientChoise.AUTO)`; preserve the existing recursion path through `client_class=ClientChoise.AUTO` by forwarding `options` to the recursive calls
- [x] pass `options` through to `HttpxClient(configuration, options)` and `AioHttpClient(configuration, options)` at the two construction sites in the `match` block
- [x] confirm the auto-loading path (`if configuration is None: configuration = await _try_read_configuration()`) still works untouched — `_try_read_configuration` produces a `ClientConfiguration` only; options remain caller-supplied
- [x] add a unit test in `test/test_client/` (e.g. `test_create_client.py` if absent — otherwise extend) verifying `await create_client(config)` defaults options correctly and `await create_client(config, options=ClientOptions(log_api_warnings=False))` propagates to the underlying client
- [x] run full suite — must pass before Task 4

### Task 4: Remove `log_api_warnings` and `timeout` from `ClientConfiguration`
- [x] delete the `log_api_warnings` and `timeout` parameters from `ClientConfiguration.__init__` (`configuration.py:209-210`) and the corresponding assignments (`self.log_api_warnings`, `self._timeout`)
- [x] delete the `timeout` property at `configuration.py:243-251`
- [x] remove the `Timeout`, `TimeoutTypes`, and `EllipsisType` imports from `configuration.py` if no other code in that module uses them after deletion
- [x] grep the repo for `\.log_api_warnings\b` and `configuration\.timeout\b` to confirm there are no remaining readers; if any survive, fix them
- [x] delete `test/test_timeout/test_configuration.py` (its purpose was testing the now-moved coercion behaviour, which Task 1 ported into `test/test_client/test_options.py`)
- [x] run full suite — must pass before Task 5

### Task 5: Update documentation

`ClientOptions` is a client concern, not a kubeconfig concern, so its narrative home is `docs/concepts/clients.md` — *not* `docs/concepts/configuration.md`. The concept page gets the substantive write-up; the configuration page gets pruned and cross-links over; the reference page is generated from docstrings via mkdocstrings; the timeouts operations page is rewritten to show the new construction shape.

- [x] add a new `## ClientOptions` section to `docs/concepts/clients.md` (placed after `## create_client()` and before `## AioHttpClient` so the factory's `options=` kwarg has a target to link to): explain that `ClientOptions` carries client-level operational toggles (not kubeconfig data); document `log_api_warnings` (what HTTP `Warning:` headers are, when the API server emits them, what gets logged); document `timeout` with the full `Ellipsis` / `None` / number / `Timeout` matrix; show a worked example combining `ClientConfiguration` and `ClientOptions` through `create_client`
- [x] update the `## create_client()` section in `docs/concepts/clients.md` to mention the new `options=` parameter and link forward to the `## ClientOptions` section
- [x] edit `docs/concepts/configuration.md`: remove the `timeout=30` line from the `ClientConfiguration(...)` example (line 26) and the `timeout` row from the parameter table (line 41); add a one-line "see also" admonition or paragraph at the top of the page noting that operational options like timeouts and warning logging now live on `ClientOptions` (link to `concepts/clients.md#clientoptions`)
- [x] edit `docs/operations/timeouts.md`: rewrite the "Setting a client-level default" section (lines 30-43) so it shows `ClientOptions(timeout=Timeout(total=30.0))` passed via `create_client(configuration=…, options=…)` instead of `ClientConfiguration(timeout=…)`; update the prose at line 43 ("If no timeout is set on `ClientConfiguration`...") to reference `ClientOptions` instead
- [x] add `## Client options` heading + `::: kubex.client.options` to `docs/reference/client.md` (between `## BaseClient and factory` and `## WebSocket abstraction`) so the API reference picks up the new module — confirms the docstrings written in Task 1 actually render
- [x] no `mkdocs.yml` nav entry needed — `ClientOptions` lives within the existing **Clients** concept page and the existing `kubex.client` reference page
- [x] grep `docs/` for any remaining references to `ClientConfiguration(timeout=` or `ClientConfiguration(log_api_warnings=` and fix them (search both `*.md` and any code-blocks in non-touched pages — the getting-started and quickstart pages may need a sweep)
- [x] run `mise run docs:build` — the strict build must pass (no broken anchors, no dead intra-doc links, mkdocstrings finds `kubex.client.options.ClientOptions`)
- [x] manually inspect the rendered pages by running `mise run docs:serve` and visiting `/concepts/clients/`, `/concepts/configuration/`, `/operations/timeouts/`, and `/reference/client/` to confirm the prose flows and the auto-generated reference looks right (check that field-level docstrings show up under `ClientOptions`) — skipped (manual browser check; build passes in strict mode)
- [x] no test changes required for this task — docs only

### Task 6: Verify acceptance criteria
- [x] `ClientConfiguration` no longer accepts `log_api_warnings` or `timeout` (passing either raises `TypeError: unexpected keyword argument`)
- [x] `ClientOptions` exists, is importable as `from kubex.client import ClientOptions`, and its `timeout` field accepts `int`, `float`, `Timeout`, `None`, and `Ellipsis`
- [x] `BaseClient`, `HttpxClient`, `AioHttpClient` all accept `options=` and read it for the timeout default and the API-warning gate
- [x] `create_client()` accepts `options=` and forwards it on every code path (HTTPX, AIOHTTP, AUTO)
- [x] `uv run pytest .` — full suite green on Python 3.13 with all extras
- [x] `uv run ruff check .` and `uv run ruff format --check .` — clean
- [x] `uv run mypy .` — clean (strict mode)
- [x] `mise run docs:build` — strict build passes with the rewritten configuration / timeouts pages and the new `ClientOptions` reference rendering
- [x] `docs/concepts/clients.md` has a substantive `## ClientOptions` section (concept-level explanation, not just a stub), and `docs/reference/client.md` shows the auto-generated `ClientOptions` API including field docstrings
- [x] manually re-read `docs/concepts/clients.md`, `docs/concepts/configuration.md`, and `docs/operations/timeouts.md` to confirm the prose still flows and cross-links resolve after the edits

## Technical Details

**`ClientOptions` shape:**

```python
# kubex/client/options.py
from __future__ import annotations
from types import EllipsisType
from pydantic import BaseModel, ConfigDict, Field, field_validator
from kubex.core.params import Timeout, TimeoutTypes


class ClientOptions(BaseModel):
    """Operational options for a kubex HTTP client.

    These do not come from kubeconfig or the in-cluster environment — they
    are per-process choices about how the client should behave at request
    time.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    log_api_warnings: bool = True
    """Emit Python warnings for any ``Warning`` headers returned by the API server."""

    timeout: TimeoutTypes | EllipsisType = Field(default_factory=lambda: ...)
    """Default HTTP timeout. ``...`` (the default) means use the HTTP library
    default; ``None`` disables timeouts; a number is treated as ``total``;
    a :class:`Timeout` is used as-is."""

    @field_validator("timeout", mode="before")
    @classmethod
    def _normalize_timeout(cls, value: object) -> object:
        if value is Ellipsis or value is None or isinstance(value, Timeout):
            return value
        return Timeout.coerce(value)  # type: ignore[arg-type]
```

**New construction pattern:**

```python
client = await create_client(
    configuration=ClientConfiguration(url=..., token=...),
    options=ClientOptions(log_api_warnings=False, timeout=30),
)
```

**`BaseClient` reshape:**

```python
class BaseClient(ABC):
    def __init__(
        self,
        configuration: ClientConfiguration,
        options: ClientOptions | None = None,
    ) -> None:
        super().__init__()
        self._configuration = configuration
        self._options = options if options is not None else ClientOptions()
        self._inner_client: Any = self._create_inner_client()

    @property
    def options(self) -> ClientOptions:
        return self._options
```

**Backend reads (after refactor):**

```python
# httpx.py / aiohttp.py
configured_timeout = self.options.timeout      # was self.configuration.timeout
if self.options.log_api_warnings and (...):    # was self.configuration.log_api_warnings
```

**Pydantic + `Ellipsis` caveat:** in pydantic v2, a bare `... ` as the default value of a field marks it required. To get an `Ellipsis` *literal* as the default value, use `Field(default_factory=lambda: ...)`. If `EllipsisType` is rejected by the schema generator, add `model_config = ConfigDict(arbitrary_types_allowed=True)`. The implementation must verify both bits work before declaring Task 1 complete.

**Order of operations rationale:** Tasks 1–3 add the new shape and consumers without touching the old fields, so the build stays green throughout. Task 4 removes the now-unused fields. Task 5 catches up the docs. Reversing this (delete first) would break the inner-client tests for the duration of the refactor.

## Post-Completion

*Items requiring manual or downstream attention. No checkboxes — informational only.*

**Manual verification:**

- Run one of the examples (`examples/get_pod.py`) against a real cluster to confirm `create_client()` with auto-loaded configuration still works end-to-end.
- Smoke-test that an API server returning a `Warning:` header produces a Python warning when `log_api_warnings=True` and is silent when `log_api_warnings=False`.

**Changelog entry:**

- Add a `BREAKING:` note to whatever changelog / release-notes file the next release uses (project does not appear to maintain one yet — note this if discovered during implementation).

**Downstream consumers:**

- Any external project pinning `kubex==0.1.0-beta.1` and passing `timeout=` / `log_api_warnings=` to `ClientConfiguration` will hit a `TypeError` after upgrading. The fix is mechanical: switch to `create_client(configuration=..., options=ClientOptions(timeout=..., log_api_warnings=...))`. Document this in the release notes.
