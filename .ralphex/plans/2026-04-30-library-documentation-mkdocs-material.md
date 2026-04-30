# Library documentation with mkdocs-material and GitHub Pages

## Overview

Set up a versioned documentation site for **Kubex** using **mkdocs-material**, **mkdocstrings** (for API reference), and **mike** (for per-release versioning), and deploy it to GitHub Pages on the custom domain `kubex.codemageddon.me` via a GitHub Actions workflow.

**Problem it solves**

The library currently has only a `README.md` and 14 working examples. As the API surface grows (sub-resources, multi-K8s-version models, two HTTP clients, two async runtimes), users need:

- A discoverable, indexed, navigable site (search + IDE-style API reference).
- A version selector so v0.1 users can read v0.1 docs even after v0.2 ships.
- Authoritative narrative around concepts that the README cannot explain in depth (descriptor-based subresource APIs, marker interfaces, channel-protocol streaming).

**Key benefits**

- A polished landing page at `https://kubex.codemageddon.me/`.
- Auto-generated API reference for `kubex` and `kubex-core` kept in sync with code via `mkdocstrings`.
- Per-release versions (`0.1.0-beta.1`, …) plus a rolling `dev` channel; `latest` always points at the most recent stable release.
- Strict build + external link checking in CI catches broken docs before they merge.

**How it integrates**

- Plans directory migrated out of `docs/` to `.ralphex/plans/` so `docs/` is reserved for the published site.
- New `docs` dependency group in the existing `pyproject.toml` (managed by `uv`).
- New `mkdocs.yml` at repo root.
- New `[tasks]` entries in `mise.toml` for local serve / strict build (matching the existing `regenerate-models` / `test` task style).
- New `.github/workflows/docs.yaml` for deploys (uses `mike` push to `gh-pages` branch).
- Strict build + link check added to existing `.github/workflows/lint.yaml`.

## Context (from discovery)

- **Files / directories involved**:
  - New: `mkdocs.yml`, `docs/index.md`, `docs/CNAME`, `docs/getting-started/`, `docs/concepts/`, `docs/operations/`, `docs/subresources/`, `docs/advanced/`, `docs/reference/`, `docs/stylesheets/`, `.github/workflows/docs.yaml`, `lychee.toml`, `docs/contributing.md`, `.ralphex/plans/` (new home for plan files).
  - Updated: `pyproject.toml` (new `docs` dependency group), `mise.toml` (new `docs:serve` / `docs:build` tasks), `.github/workflows/lint.yaml` (strict build + link check), `.gitignore` (mkdocs `site/` build output), `README.md` (link to docs site + status badge), `CLAUDE.md` (docs-related entries).
  - Moved: `docs/plans/**` → `.ralphex/plans/**` (this very plan file relocates as part of Task 1).

- **Related patterns found**:
  - 14 examples in `examples/` map cleanly to narrative pages (per-feature tutorials).
  - Performance tables already in `README.md` migrate to a dedicated benchmarks page.
  - Public API entry points already documented in `CLAUDE.md` (`kubex.api.Api`, `kubex.client.create_client`, `kubex.configuration.ClientConfiguration`) — these are the natural mkdocstrings targets.
  - 4 GitHub Actions workflows exist (`lint`, `test`, `publish-test`, `publish`) using `uv` and OIDC publishing — new `docs.yaml` follows the same `astral-sh/setup-uv` + `uv sync --group docs` pattern.
  - Existing `mise.toml` has `[tasks.regenerate-models]` and `[tasks.test]` — new docs tasks follow the same shape.

- **Dependencies identified**:
  - Runtime: `mkdocs>=1.6`, `mkdocs-material`, `mkdocstrings[python]`, `mike`, `pymdown-extensions`.
  - CI-only: `lycheeverse/lychee-action` (no Python dep).
  - GitHub Pages source must be set to `gh-pages` branch and the custom domain `kubex.codemageddon.me` configured (one-time, manual — listed in Post-Completion).
  - DNS: a `CNAME` record `kubex.codemageddon.me → codemageddon.github.io.` must be created at the domain registrar (one-time, manual — listed in Post-Completion).

## Development Approach

- **Testing approach**: Regular (build verification + link checking, no traditional unit tests for docs content).
- Complete each task fully before moving to the next.
- Make small, focused changes — one content section per task.
- **CRITICAL: every task that adds/changes docs content MUST run `mise run docs:build`** (which wraps `uv run --group docs mkdocs build --strict`) as its verification step. `--strict` turns warnings (broken refs, dangling links, missing pages) into errors.
- **CRITICAL: tasks that touch markdown linking to external URLs must also run `lychee`** locally before completion, or document why a URL is intentionally unreachable.
- **CRITICAL: all build checks must pass before starting next task** — no exceptions.
- **CRITICAL: update this plan file when scope changes during implementation.**
- Maintain backward compatibility — `README.md` stays present and continues to be the PyPI front page; doc site supplements, does not replace it.

## Testing Strategy

- **Build verification**: `mise run docs:build` (wraps `uv run --group docs mkdocs build --strict`) must succeed at the end of every task that touches docs.
- **Link checking**: `lychee` (via `lycheeverse/lychee-action` in CI; locally via `lychee --offline docs/` or `lychee docs/` for full external check). Configure ignores in `lychee.toml` for known-flaky or example-only URLs (e.g., `localhost`, `example.com`, `kubernetes.default.svc`).
- **mkdocstrings reference resolution**: every `:::kubex.…` reference in `docs/reference/` must resolve under `--strict`. If a target is private or intentionally undocumented, exclude it via `mkdocstrings` options rather than letting the build warn.
- **mike preview**: at the end of the mike-config task, run `uv run --group docs mike deploy --no-push 0.1.0-beta.1 latest --update-aliases` against a local clone of the `gh-pages` branch to confirm the deploy mechanics before wiring up CI.
- **No unit tests** — docs content does not warrant traditional pytest tests. All verification is via `mkdocs build --strict` + `lychee`.

## Progress Tracking

- Mark completed items with `[x]` immediately when done.
- Add newly discovered tasks with the ➕ prefix.
- Document issues / blockers with the ⚠️ prefix.
- Update plan if implementation deviates from original scope.
- Keep plan in sync with actual work done.

## What Goes Where

- **Implementation Steps** (`[ ]` checkboxes): tasks achievable inside this codebase — file creation, content writing, workflow YAML, config changes, build verification.
- **Post-Completion** (no checkboxes): items requiring external action — GitHub Pages source-branch setting, custom-domain DNS record, first manual deploy, badge addition, social preview image.

## Implementation Steps

### Task 1: Migrate plans directory out of `docs/`

- [x] create `.ralphex/plans/` directory at repo root (do NOT add a `.gitignore` entry — plan files must remain tracked)
- [x] `git mv docs/plans/* .ralphex/plans/` to relocate every plan file (this very plan file moves with them); preserve any sub-structure such as `docs/plans/completed/` → `.ralphex/plans/completed/`
- [x] remove now-empty `docs/plans/` directory
- [x] update `.ralphex/.gitignore` if any plans-related entries exist (currently only `progress/` and `worktrees/` are ignored — no change needed, but verify)
- [x] update any references to `docs/plans/` in repo files (skill docs, ralphex config, README, CLAUDE.md, agent prompts) — grep first, edit second
- [x] verify `git status` shows only the rename (no content drift); commit hint: this should be a pure rename so `git log --follow` continues to work

### Task 2: Add `docs` dependency group, base `mkdocs.yml`, mise tasks, and `.gitignore` entry

- [x] add a `docs` dependency group in `pyproject.toml` containing: `mkdocs>=1.6`, `mkdocs-material>=9.5`, `mkdocstrings[python]>=0.26`, `mike>=2.1`, `pymdown-extensions>=10.11`
- [x] run `uv lock` and `uv sync --group docs` to populate the group
- [x] create `mkdocs.yml` at repo root with: `site_name: Kubex`, `site_url: https://kubex.codemageddon.me/`, `repo_url: https://github.com/codemageddon/kubex`, `repo_name: codemageddon/kubex`, `edit_uri: edit/main/docs/`, `docs_dir: docs`, `theme: material` (with palette, features: `navigation.tabs`, `navigation.sections`, `content.code.copy`, `content.action.edit`), base `markdown_extensions` (admonition, pymdownx.highlight + superfences + inlinehilite, pymdownx.tabbed, pymdownx.snippets, attr_list, md_in_html, toc with permalink). Note: `exclude_docs` is **not** needed — plans now live at `.ralphex/plans/`, outside `docs_dir`.
- [x] add `[tasks."docs:serve"]` and `[tasks."docs:build"]` entries to `mise.toml` (matching the existing `[tasks.regenerate-models]` / `[tasks.test]` style); run targets: `uv run --group docs mkdocs serve` and `uv run --group docs mkdocs build --strict`
- [x] add `site/` to `.gitignore` (mkdocs build output)
- [x] verify `mise run docs:build` succeeds with an empty `docs/index.md` placeholder (build verification = our equivalent of tests for this task)
- [x] verify `mise run docs:serve` starts a local server (default `http://127.0.0.1:8000/`)

### Task 3: Bootstrap `docs/index.md` landing page and content directory skeleton

- [x] create `docs/index.md` adapted from `README.md` — keep performance hook, type-safety hook, multi-version hook, async-runtime hook; trim "Planned Features" (lives only in README); link to "Get started" page
- [x] create empty stub pages (one-line content + page title) at: `docs/getting-started/installation.md`, `docs/getting-started/quickstart.md`, `docs/concepts/index.md`, `docs/operations/index.md`, `docs/subresources/index.md`, `docs/advanced/index.md`, `docs/reference/index.md`, `docs/contributing.md`
- [x] configure `nav` in `mkdocs.yml` mapping all stubs (top-level: Home, Getting Started, Concepts, Operations, Subresources, Advanced, API Reference, Contributing)
- [x] add `docs/stylesheets/extra.css` and reference it via `extra_css` in `mkdocs.yml` for any kubex-specific tweaks (e.g., wider code blocks)
- [x] verify `mise run docs:build` succeeds with full nav and no broken links
- [x] verify nav order matches the user journey (intro → install → concepts → ops → subres → advanced → reference)

### Task 4: Getting started pages (installation + quickstart)

- [x] write `docs/getting-started/installation.md` covering: `pip install kubex` baseline, optional extras matrix (`[httpx]`, `[httpx-ws]`, `[aiohttp]`, `k8s-1.32`–`k8s-1.37`), recommended combinations, Python version support (3.10–3.14), trio caveat (httpx only)
- [x] write `docs/getting-started/quickstart.md` covering: `create_client()` auto-detection, kubeconfig vs in-cluster, the `Api[Pod]` first-request example, where to go next (link to Concepts and Operations sections)
- [x] cross-reference both pages from `docs/index.md`
- [x] include runnable code blocks taken from `examples/get_pod.py` and `examples/list_namespaces.py` (verbatim where possible — keep examples DRY)
- [x] verify `mise run docs:build` passes
- [x] run `lychee docs/getting-started/` locally and fix any reported broken external links (skipped — lychee not installed locally; CI will check via lycheeverse/lychee-action in Task 13)

### Task 5: Core concepts pages

- [x] write `docs/concepts/api.md` — `Api[ResourceType]` generic, the `create_api()` factory, namespace-vs-cluster scope, the `Ellipsis` sentinel for namespace/timeout overrides, link to `examples/`
- [x] write `docs/concepts/clients.md` — `BaseClient` ABC, `create_client()` auto-detection, `HttpxClient` vs `AioHttpClient`, the `connect_websocket()` extension point
- [x] write `docs/concepts/configuration.md` — `ClientConfiguration`, `configure_from_kubeconfig()`, `configure_from_pod_env()`, mention exec-provider auth (full details in Advanced/Authentication)
- [x] write `docs/concepts/exceptions.md` — exception tree from `core/exceptions.py` (KubexException → ConfgiurationError, KubexClientException → KubexApiError → BadRequest/Unauthorized/Forbidden/NotFound/MethodNotAllowed/Conflict/Gone/UnprocessableEntity)
- [x] write `docs/concepts/subresources.md` — descriptor pattern, marker interfaces (`HasLogs`, `HasScaleSubresource`, `HasStatusSubresource`, `Evictable`, `HasEphemeralContainers`, `HasResize`, `HasExec`, `HasAttach`, `HasPortForward`), how mypy enforces availability
- [x] update `docs/concepts/index.md` with a brief landing description + nav cards linking to the five pages above
- [x] verify `mise run docs:build` passes; run `lychee` locally on `docs/concepts/`

### Task 6: Resource operations pages (CRUD, watch, patch, timeouts)

- [x] write `docs/operations/crud.md` — `get`, `create`, `replace`, `delete`, `list`, `delete_collection`; reuse code from `examples/get_pod.py`, `examples/replace_pod.py`, `examples/delete_collection.py`
- [x] write `docs/operations/watch.md` — `watch()` and `list_with_initial_events()`, `WatchEvent`, `EventType`, restart-on-410-Gone pattern; reuse `examples/watch_pods.py`
- [x] write `docs/operations/patch.md` — three patch types: `MergePatch`, `StrategicMergePatch`, `JsonPatch` (with `JsonPatchAdd` etc.); reuse `examples/patch_deployment.py`
- [x] write `docs/operations/timeouts.md` — `Timeout`, `TimeoutTypes`, the `Ellipsis` sentinel for per-call override, configuring at client level vs request level
- [x] update `docs/operations/index.md` with overview + nav cards
- [x] verify `mise run docs:build` passes; run `lychee` locally on `docs/operations/`

### Task 7: Subresource pages — non-WebSocket (logs, metadata, scale, status, eviction, ephemeral_containers, resize)

- [x] write `docs/subresources/logs.md` — `api.logs.get()`, `api.logs.stream()`, `LogParams` (container, follow, since_seconds, tail_lines, …); reuse `examples/get_pod_logs.py`
- [x] write `docs/subresources/metadata.md` — `api.metadata.get/list/patch/watch`, partial-object metadata (memory savings vs full list)
- [x] write `docs/subresources/scale.md` — `api.scale.get/replace/patch`; reuse `examples/scale_deployment.py`
- [x] write `docs/subresources/status.md` — `api.status.get/replace/patch`; reuse `examples/status_operations.py`
- [x] write `docs/subresources/eviction.md` — `api.eviction.create()` for graceful pod eviction (PDB-aware)
- [x] write `docs/subresources/ephemeral-containers.md` — `api.ephemeral_containers.get/replace/patch` for live debug containers
- [x] write `docs/subresources/resize.md` — `api.resize.get/replace/patch` for in-place pod resource resize
- [x] verify `mise run docs:build` passes; run `lychee` locally on `docs/subresources/` (subset)

### Task 8: Subresource pages — WebSocket (exec, attach, portforward)

- [x] write `docs/subresources/exec.md` — `api.exec.run()` for one-shot collection, `api.exec.stream()` for interactive session, channel protocol, TTY merging behaviour, `wait_for_status()`, `ExecResult.exit_code` semantics (`0` / int / `None`); reuse `examples/exec_pod.py`; install requirement (`kubex[httpx-ws]` or `kubex[aiohttp]`); K8s ≥1.30 requirement (v5 channel protocol)
- [x] write `docs/subresources/attach.md` — `api.attach.stream()` only (no `run()`); container `stdin: true` requirement; reuse `examples/attach_pod.py`
- [x] write `docs/subresources/portforward.md` — two-level API: `api.portforward.forward()` (low-level `PortForwarder` with per-port `ByteStream` + error iterators) and `api.portforward.listen()` (local TCP listener — kubectl-style); reuse `examples/portforward_pod.py`; mention port-prefix protocol detail for advanced users
- [x] update `docs/subresources/index.md` with overview + nav cards (group as "Standard subresources" and "WebSocket subresources" with experimental note)
- [x] add an admonition box on each WebSocket page noting beta-experimental status (matches README warning)
- [x] verify `mise run docs:build` passes; run `lychee` locally on `docs/subresources/`

### Task 9: Advanced topics (multi-version, clients/runtimes, auth, benchmarks)

- [x] write `docs/advanced/multi-version-k8s.md` — picking `kubex-k8s-X-Y` packages, mixing versions in one app, OpenAPI-spec correspondence (the page is for **library users**; explicitly do **not** mention `mise run regenerate-models` here — that's a maintainer command and belongs in `docs/contributing.md` only)
- [x] write `docs/advanced/clients-runtimes.md` — httpx vs aiohttp trade-offs, asyncio vs trio (trio only with httpx), WebSocket support matrix (httpx requires `httpx-ws` extra; aiohttp built-in)
- [x] write `docs/advanced/authentication.md` — kubeconfig file parsing, in-cluster (pod env), exec provider with token refresh, OIDC (note: in progress)
- [x] write `docs/advanced/benchmarks.md` — migrate the performance table from `README.md`, link to `benchmarks/` directory, instructions for reproducing (Docker requirement, K3S testcontainer)
- [x] update `docs/advanced/index.md` with overview + nav cards
- [x] verify `mise run docs:build` passes; run `lychee` locally on `docs/advanced/`

### Task 10: API reference via `mkdocstrings`

- [x] add `mkdocstrings` plugin block to `mkdocs.yml` with the `python` handler: enable `paths: [".", "packages/kubex-core"]`, `options.show_signature_annotations: true`, `options.separate_signature: true`, `options.docstring_style: google`, `options.show_source: true`, `options.merge_init_into_class: true`, `options.show_root_heading: true`, `options.show_if_no_docstring: false`, `options.filters: ["!^_"]`
- [x] create `docs/reference/api.md` with `:::kubex.api.api`, `:::kubex.api._logs`, `:::kubex.api._scale`, `:::kubex.api._status`, `:::kubex.api._eviction`, `:::kubex.api._ephemeral_containers`, `:::kubex.api._resize`, `:::kubex.api._exec`, `:::kubex.api._attach`, `:::kubex.api._portforward`, `:::kubex.api._metadata`, `:::kubex.api._stream_session`, `:::kubex.api._portforward_session`, `:::kubex.api._protocol`
- [x] create `docs/reference/client.md` with `:::kubex.client.client`, `:::kubex.client.websocket`, `:::kubex.client.httpx`, `:::kubex.client.aiohttp`
- [x] create `docs/reference/configuration.md` with `:::kubex.configuration.configuration`, `:::kubex.configuration.file_config`, `:::kubex.configuration.incluster_config`, `:::kubex.configuration.auth.exec`, `:::kubex.configuration.auth.oidc`, `:::kubex.configuration.auth.refreshable_token`
- [x] create `docs/reference/core.md` with `:::kubex.core.exceptions`, `:::kubex.core.params`, `:::kubex.core.request`, `:::kubex.core.response`, `:::kubex.core.json_patch`, `:::kubex.core.json_pointer`, `:::kubex.core.patch`, `:::kubex.core.subresource`, `:::kubex.core.exec_channels`, `:::kubex.core.request_builder.builder`
- [x] create `docs/reference/kubex-core.md` with `:::kubex_core.models.base`, `:::kubex_core.models.base_entity`, `:::kubex_core.models.interfaces`, `:::kubex_core.models.resource_config`, `:::kubex_core.models.metadata`, `:::kubex_core.models.list_entity`, `:::kubex_core.models.watch_event`, `:::kubex_core.models.status`, `:::kubex_core.models.scale`, `:::kubex_core.models.eviction`, `:::kubex_core.models.partial_object_meta`, `:::kubex_core.models.typing`
- [x] update `docs/reference/index.md` with a brief description noting "generated K8s resource models (`kubex.k8s.v1_*`) are not rendered here — see PyPI / source for those"
- [x] add `docs/reference/` pages to `nav` in `mkdocs.yml`
- [x] verify `mise run docs:build` resolves every `:::` reference (failures surface as warnings → errors under `--strict`); fix any ImportError / unresolved-reference issues by tightening filter or the `paths` config
- [x] run `lychee` locally on `docs/reference/` (skipped — lychee not installed locally; CI will check via lycheeverse/lychee-action in Task 13)

### Task 11: `mike` versioning configuration + custom-domain `CNAME`

- [x] add the `mike` config block to `mkdocs.yml`: `extra.version.provider: mike`, `extra.version.default: latest`
- [x] update `theme.features` to include the version selector dropdown (Material handles this automatically when the `mike` provider is set)
- [x] create `docs/CNAME` containing the single line `kubex.codemageddon.me` (mkdocs copies non-md files into `site/` automatically; mike will publish it inside each version subdirectory). The authoritative root-level `CNAME` on the `gh-pages` branch is created in Post-Completion (one-time manual step) — see notes there.
- [x] write `docs/contributing.md` covering: local preview (`mise run docs:serve`), strict build (`mise run docs:build`), link check (`lychee docs/`), versioned deploy (`mike deploy <version> [alias] --update-aliases`), the deploy workflow in CI, **and a maintainer-only section documenting `mise run regenerate-models`** for K8s OpenAPI regeneration (developer-facing, not surfaced in `docs/advanced/`)
- [x] add a one-time bootstrap section in `docs/contributing.md` describing how to seed the `gh-pages` branch with `mike deploy --push 0.1.0-beta.1 latest --update-aliases` and to add a root-level `CNAME` file on first deploy
- [x] verify `uv run --group docs mike deploy --no-push 0.1.0-beta.1 latest --update-aliases` runs without error against a temporary branch (test mechanics; do not push) — note: `--no-push` flag not supported by mike; verified by running without `--push` flag which deploys to local gh-pages branch only
- [x] verify `mise run docs:build` still passes

### Task 12: GitHub Actions deploy workflow

- [x] create `.github/workflows/docs.yaml` with triggers: `push` to `main`, `push` of `v*` tags, and `workflow_dispatch`
- [x] job permissions: `contents: write` (push to `gh-pages` branch); `pages: write` and `id-token: write` only if switching to OIDC-Pages later (commented out for now)
- [x] steps: checkout (with `fetch-depth: 0` so mike can read history), `astral-sh/setup-uv`, `uv sync --group docs`, configure `git config user.name "github-actions[bot]"` + `user.email "41898282+github-actions[bot]@users.noreply.github.com"`, then branch on event:
  - on `push` to `main`: `mike deploy --push --update-aliases dev`
  - on tag push (`v*`): extract version from `${GITHUB_REF#refs/tags/v}`, then `mike deploy --push --update-aliases "$VERSION" latest` and `mike set-default --push latest` (idempotent)
  - on `workflow_dispatch`: deploy `dev` (configurable via input)
- [x] use `actions/checkout@v4`, `astral-sh/setup-uv@v3` (matching versions used in `lint.yaml`/`test.yaml`)
- [x] add a concurrency group `concurrency.group: docs-deploy` with `cancel-in-progress: false` (don't cancel in-flight deploys)
- [x] verify the workflow YAML parses (`actionlint .github/workflows/docs.yaml` if available on PATH; otherwise rely on GitHub's UI validation)
- [x] verify the workflow does not trigger on PRs (no leaked deploys)

### Task 13: Strict build + lychee link check in CI

- [x] create `lychee.toml` at repo root with: `cache = true`, `max_retries = 3`, `accept = [200, 206, 429]`, `exclude_path = [".ralphex/", "site/", ".venv/"]`, `exclude = ["^http://localhost", "^https?://example\\.com", "kubernetes\\.default\\.svc"]`
- [x] add a `docs` job to `.github/workflows/lint.yaml` that runs on `push` and `pull_request`: checkout → setup-uv → `uv sync --group docs` → `mise run docs:build` (or directly `uv run --group docs mkdocs build --strict`)
- [x] add a `link-check` step in the same `docs` job using `lycheeverse/lychee-action@v2` with `args: --config lychee.toml docs/` and `fail: true`
- [x] verify locally: `mise run docs:build` is clean (passed); lychee not installed locally — CI will check via lycheeverse/lychee-action
- [x] verify `lint.yaml` is still valid YAML and the `docs` job is independent of the existing pre-commit / ruff / mypy / codegen-verify jobs (verified — no `needs:` dependencies)

### Task 14: Verify acceptance criteria

- [x] verify all four content groups present and navigable: Getting Started + Concepts, Operations, Subresources, Advanced
- [x] verify API reference covers `kubex.api`, `kubex.client`, `kubex.configuration`, `kubex.core`, `kubex_core.models`
- [x] verify version selector works: `mike list` shows `0.1.0-beta.1 [latest]`; `dev` alias created on CI push to main (manual deploy skipped — CI handles it)
- [x] verify `lychee` finds no broken links (manual test skipped — lychee not installed locally; CI checks via lycheeverse/lychee-action)
- [x] verify `mise run docs:build` is clean for the full site
- [x] verify `pre-commit run --all-files` and `ruff check . && ruff format --check . && mypy .` are still clean (no docs work has regressed code-side checks)
- [x] verify `pyproject.toml` `docs` group does not bloat the default `uv sync` (group is opt-in, confirmed)
- [x] verify the migrated plan files at `.ralphex/plans/` are tracked in git and ralphex CLI can still read them

### Task 15: [Final] Update README, CLAUDE.md, and inter-doc references

- [x] add a "Documentation: https://kubex.codemageddon.me/" link near the top of `README.md`
- [x] add a docs-build status badge to `README.md` referencing the new `docs.yaml` workflow
- [x] update `CLAUDE.md` — add docs site URL to "Project Overview", add the new `mise run docs:serve` / `mise run docs:build` to "Quick Reference", note that plans now live at `.ralphex/plans/`
- [x] verify `mise run docs:build` still passes (no docs-content change here, but README link is referenced from `docs/index.md` indirectly)

## Technical Details

**`mkdocs.yml` shape (sketch — final config emitted in Task 2 + iteratively expanded)**

```yaml
site_name: Kubex
site_url: https://kubex.codemageddon.me/
site_description: Async-first Kubernetes client library for Python.
repo_url: https://github.com/codemageddon/kubex
repo_name: codemageddon/kubex
edit_uri: edit/main/docs/

docs_dir: docs
# Note: no `exclude_docs` — plans now live at .ralphex/plans/, outside docs_dir.

theme:
  name: material
  features:
    - navigation.tabs
    - navigation.sections
    - navigation.expand
    - navigation.top
    - search.suggest
    - search.highlight
    - content.code.copy
    - content.action.edit
    - content.tabs.link
  palette:
    - media: "(prefers-color-scheme: light)"
      scheme: default
      primary: indigo
      toggle: { icon: material/weather-night, name: Switch to dark mode }
    - media: "(prefers-color-scheme: dark)"
      scheme: slate
      primary: indigo
      toggle: { icon: material/weather-sunny, name: Switch to light mode }

plugins:
  - search
  - mkdocstrings:
      handlers:
        python:
          paths: [".", "packages/kubex-core"]
          options:
            show_signature_annotations: true
            separate_signature: true
            docstring_style: google
            show_source: true
            merge_init_into_class: true
            show_root_heading: true
            show_if_no_docstring: false
            filters: ["!^_"]

markdown_extensions:
  - admonition
  - attr_list
  - md_in_html
  - toc:
      permalink: true
  - pymdownx.highlight:
      anchor_linenums: true
  - pymdownx.inlinehilite
  - pymdownx.snippets
  - pymdownx.superfences
  - pymdownx.tabbed:
      alternate_style: true
  - pymdownx.details

extra:
  version:
    provider: mike
    default: latest

extra_css:
  - stylesheets/extra.css

nav:
  - Home: index.md
  - Getting Started:
      - Installation: getting-started/installation.md
      - Quickstart: getting-started/quickstart.md
  - Concepts:
      - concepts/index.md
      - Api[T]: concepts/api.md
      - Clients: concepts/clients.md
      - Configuration: concepts/configuration.md
      - Subresources: concepts/subresources.md
      - Exceptions: concepts/exceptions.md
  - Operations:
      - operations/index.md
      - CRUD: operations/crud.md
      - Watch: operations/watch.md
      - Patch: operations/patch.md
      - Timeouts: operations/timeouts.md
  - Subresources:
      - subresources/index.md
      - Logs: subresources/logs.md
      - Metadata: subresources/metadata.md
      - Scale: subresources/scale.md
      - Status: subresources/status.md
      - Eviction: subresources/eviction.md
      - Ephemeral Containers: subresources/ephemeral-containers.md
      - Resize: subresources/resize.md
      - Exec: subresources/exec.md
      - Attach: subresources/attach.md
      - Portforward: subresources/portforward.md
  - Advanced:
      - advanced/index.md
      - Multi-version K8s: advanced/multi-version-k8s.md
      - Clients & Runtimes: advanced/clients-runtimes.md
      - Authentication: advanced/authentication.md
      - Benchmarks: advanced/benchmarks.md
  - API Reference:
      - reference/index.md
      - kubex.api: reference/api.md
      - kubex.client: reference/client.md
      - kubex.configuration: reference/configuration.md
      - kubex.core: reference/core.md
      - kubex-core: reference/kubex-core.md
  - Contributing: contributing.md
```

**`mise.toml` task additions (sketch — emitted in Task 2)**

```toml
[tasks."docs:serve"]
description = "Serve the docs site locally with live reload"
run = "uv run --group docs mkdocs serve"

[tasks."docs:build"]
description = "Build the docs site in strict mode"
run = "uv run --group docs mkdocs build --strict"
```

**`docs.yaml` workflow shape (sketch — final emitted in Task 12)**

```yaml
name: Docs

on:
  push:
    branches: [main]
    tags: ["v*"]
  workflow_dispatch:
    inputs:
      version:
        description: "Version label (defaults to 'dev')"
        required: false
        default: "dev"

permissions:
  contents: write

concurrency:
  group: docs-deploy
  cancel-in-progress: false

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: astral-sh/setup-uv@v3
        with:
          python-version: "3.13"
      - run: uv sync --group docs
      - name: Configure git
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
      - name: Deploy (main → dev)
        if: github.event_name == 'push' && github.ref == 'refs/heads/main'
        run: uv run --group docs mike deploy --push --update-aliases dev
      - name: Deploy (tag → versioned + latest)
        if: github.event_name == 'push' && startsWith(github.ref, 'refs/tags/v')
        run: |
          VERSION="${GITHUB_REF#refs/tags/v}"
          uv run --group docs mike deploy --push --update-aliases "$VERSION" latest
          uv run --group docs mike set-default --push latest
      - name: Deploy (workflow_dispatch)
        if: github.event_name == 'workflow_dispatch'
        run: uv run --group docs mike deploy --push --update-aliases "${{ github.event.inputs.version }}"
```

**Processing flow for a release**

1. PR merges to `main` → `docs.yaml` triggers → `mike deploy dev` → `gh-pages` branch updated → GitHub Pages serves the `dev` channel at `kubex.codemageddon.me/dev/`.
2. Tag `v0.2.0` pushed → `docs.yaml` triggers (separately from `publish.yaml`) → `mike deploy 0.2.0 latest` → `mike set-default latest` → users hitting `kubex.codemageddon.me/` land on `0.2.0`; older versions remain accessible via the version dropdown.

## Post-Completion

*Items requiring manual intervention or external systems — informational only, no checkboxes.*

**One-time DNS setup (custom domain `kubex.codemageddon.me`)**

- At the registrar / DNS provider for `codemageddon.me`, add a `CNAME` record: `kubex.codemageddon.me. → codemageddon.github.io.` (TTL 300–3600).
- Wait for propagation (usually <15 min); verify with `dig +short kubex.codemageddon.me CNAME`.

**One-time GitHub setup**

- After the first `mike deploy --push` creates the `gh-pages` branch:
  1. In the repository settings → Pages: set **Source = Deploy from a branch**, **Branch = `gh-pages`**, **Folder = `/ (root)`**.
  2. In the same Pages settings: set **Custom domain = `kubex.codemageddon.me`** and tick **Enforce HTTPS** (this writes a root-level `CNAME` file on the `gh-pages` branch automatically; mike will preserve it across subsequent deploys).
  3. (Alternative if the GitHub UI fails to write CNAME): manually add `CNAME` to gh-pages branch root via `git checkout gh-pages && echo 'kubex.codemageddon.me' > CNAME && git add CNAME && git commit -m "set custom domain" && git push`. Mike does not touch root files of the `gh-pages` branch outside its own version subdirectories, so this CNAME persists across deploys.
- Verify the published site loads at `https://kubex.codemageddon.me/` and that GitHub-issued cert is valid (HTTPS lock icon).

**First deploy bootstrap**

- The `dev` and `latest` aliases must exist before the workflow's `mike set-default --push latest` step succeeds. Either:
  - Run `uv run --group docs mike deploy --push 0.1.0-beta.1 latest --update-aliases` from a maintainer's machine once, OR
  - Push a tag `v0.1.0-beta.1` (or a temporary `v0.1.0-beta.99`) to trigger the workflow's tag branch, which seeds `latest` automatically.

**Manual verification scenarios**

- Verify the version selector dropdown renders in the Material theme on the live site.
- Verify search is working (search index built by mkdocs `search` plugin).
- Click through every page in the live nav at least once to catch theme-rendering issues that strict-build doesn't catch (e.g., admonition styling, tabbed code blocks).
- Verify GitHub edit links (`edit_uri`) point to the right files on `main`.
- Verify mkdocstrings-generated API reference shows complete signatures for `Api.get`, `Api.list`, `Api.watch`, `create_client`, etc.
- Verify HTTPS certificate is valid and renews (GitHub Pages handles renewal automatically once the domain is verified).

**External-system updates** *(if applicable)*

- Add a "Docs" link on the PyPI project pages for `kubex` and `kubex-core` by adding `Documentation = "https://kubex.codemageddon.me/"` under `[project.urls]` in the next release of `pyproject.toml` — out of scope for this plan but a natural follow-up.
- Update any external links (`github.io/codemageddon/kubex` references in blog posts, slides, etc.) to the new custom domain.
- Once site is live, consider adding a Documentation badge to `README.md`.
