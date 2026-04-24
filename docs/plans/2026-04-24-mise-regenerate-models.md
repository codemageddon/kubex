# Mise Task for Automatic Model Package Regeneration

## Overview
- Add a `regenerate-models` mise task that downloads the latest Kubernetes OpenAPI swagger specs and regenerates all `kubex-k8s-*` model packages
- The task resolves the latest patch/pre-release tag for each configured minor version (e.g. 1.32 -> v1.32.13, 1.37 -> v1.37.0-alpha.0), downloads both the v2 swagger.json and all v3 per-group OpenAPI specs from the Kubernetes GitHub repo, runs codegen with `--v3-dir`, and verifies the output
- Must be cross-platform (macOS, Linux, Windows via Python — no shell scripts)

## Context (from discovery)
- Files/components involved:
  - `mise.toml` — add task definition with explicit version list
  - `scripts/codegen/__main__.py` — existing codegen CLI (generate + verify commands)
  - `scripts/codegen/spec_loader.py` — loads swagger.json from local path
  - `packages/kubex-k8s-{1-32..1-37}/` — generated model packages
  - `.gitignore` — needs `.cache/` entry
- Related patterns found:
  - Codegen CLI: `uv run python -m scripts.codegen generate --swagger <path> --k8s-version <ver>`
  - Verify CLI: `uv run python -m scripts.codegen verify packages/kubex-k8s-<ver>`
  - Swagger v2 spec at: `https://raw.githubusercontent.com/kubernetes/kubernetes/<tag>/api/openapi-spec/swagger.json`
  - V3 per-group specs at: `https://raw.githubusercontent.com/kubernetes/kubernetes/<tag>/api/openapi-spec/v3/<filename>.json` (~64 files per version)
  - V3 file listing via: `https://api.github.com/repos/kubernetes/kubernetes/contents/api/openapi-spec/v3?ref=<tag>`
  - GitHub Releases API: `https://api.github.com/repos/kubernetes/kubernetes/releases` (paginated, filter by tag prefix)
- Dependencies identified:
  - `urllib` (stdlib) for HTTP — no external deps needed
  - GitHub API for release tag resolution (unauthenticated, 60 req/hour rate limit is sufficient)
  - Existing codegen deps (`jinja2`, `typer`, `ruff`, `mypy`) already in dev dependencies

## Development Approach
- **Testing approach**: Regular (code first, then tests)
- Complete each task fully before moving to the next
- Make small, focused changes
- **CRITICAL: every task MUST include new/updated tests** for code changes in that task
- **CRITICAL: all tests must pass before starting next task**
- **CRITICAL: update this plan file when scope changes during implementation**
- Run tests after each change
- Maintain backward compatibility

## Testing Strategy
- **Unit tests**: required for every task — test release resolution logic, download caching, version parsing
- **E2E tests**: not applicable (this is a dev tooling task, not user-facing code)

## Progress Tracking
- Mark completed items with `[x]` immediately when done
- Add newly discovered tasks with ➕ prefix
- Document issues/blockers with ⚠️ prefix
- Update plan if implementation deviates from original scope
- Keep plan in sync with actual work done

## Implementation Steps

### Task 1: Add Python helper script for release resolution and spec downloading
- [x] Create `scripts/codegen/fetch_specs.py` with:
  - `resolve_latest_release(minor_version: str) -> str` — queries GitHub Releases API to find the latest release tag for a given minor version (e.g. `"1.32"` -> `"v1.32.13"`). Must handle pagination (100 per page). For pre-release-only versions (e.g. 1.37), fall back to git tags API (`/repos/kubernetes/kubernetes/git/refs/tags/v1.37`) to find the latest alpha/beta/rc tag
  - `download_specs(tag: str, cache_dir: Path) -> DownloadedSpecs` — downloads both v2 and v3 specs for a given full release tag:
    - v2: `swagger.json` from `https://raw.githubusercontent.com/kubernetes/kubernetes/<tag>/api/openapi-spec/swagger.json` into `<cache_dir>/<tag>/swagger.json`
    - v3: lists files via GitHub Contents API (`/repos/kubernetes/kubernetes/contents/api/openapi-spec/v3?ref=<tag>`), downloads each `.json` file into `<cache_dir>/<tag>/v3/<filename>.json`
    - Skips download if `<cache_dir>/<tag>/swagger.json` already exists (cache hit for the whole tag)
    - Returns a `DownloadedSpecs` dataclass with `swagger_path: Path` and `v3_dir: Path`
  - `fetch_all_specs(minor_versions: list[str], cache_dir: Path) -> dict[str, DownloadedSpecs]` — orchestrates resolution + download for a list of minor versions. Returns mapping of minor version to downloaded spec paths
- [x] Use only `urllib.request` (stdlib) for HTTP — no external dependencies
- [x] Add proper error handling: HTTP errors, rate limiting (retry with backoff), missing releases
- [x] Write unit tests in `scripts/codegen/tests/test_fetch_specs.py`:
  - Test `resolve_latest_release` with mocked GitHub API responses (stable release, pre-release-only, no releases found)
  - Test `download_specs` cache hit/miss logic (mock HTTP, use tmp_path for cache dir)
  - Test v3 file listing and download (mock Contents API response)
  - Test `fetch_all_specs` orchestration
- [x] Run tests — must pass before next task

### Task 2: Add `regenerate` CLI command to the codegen module
- [ ] In `scripts/codegen/__main__.py`, add a new `regenerate` typer command that:
  - Accepts `--versions` (comma-separated minor versions, e.g. `"1.32,1.33,1.34,1.35,1.36,1.37"`) — required
  - Accepts `--cache-dir` (default: `.cache/schemas`)
  - Accepts `--package-version` (default: `"0.1.0-alpha.1"`)
  - Accepts `--output` (default: `packages/`)
  - Accepts `--verify/--no-verify` (default: `--verify`)
  - Calls `fetch_all_specs()` to resolve and download all swagger + v3 specs
  - Iterates over each version: runs `generate` logic with both `--swagger` and `--v3-dir` from the downloaded specs (reuse existing code), then optionally `verify`
  - Reports summary at the end (success/failure per version)
- [ ] Refactor the existing `generate` command body into a reusable function so `regenerate` can call it without subprocess overhead
- [ ] Write unit tests in `scripts/codegen/tests/test_regenerate_command.py`:
  - Test CLI argument parsing (invoke via typer.testing.CliRunner)
  - Test that regenerate calls fetch + generate + verify in correct order (mock the heavy operations)
- [ ] Run tests — must pass before next task

### Task 3: Add mise task configuration
- [ ] Add `[tasks.regenerate-models]` to `mise.toml`:
  - `run = "uv run python -m scripts.codegen regenerate --versions {{env.K8S_VERSIONS}}"`
  - Define `K8S_VERSIONS` env var with explicit version list: `"1.32,1.33,1.34,1.35,1.36,1.37"`
  - Add description: `"Download latest K8s OpenAPI specs and regenerate all model packages"`
- [ ] Add `.cache/` to `.gitignore` if not already present
- [ ] Verify `mise run regenerate-models` works end-to-end (dry run or with one version)
- [ ] Write no new tests (mise config is verified by running the task)
- [ ] Run existing tests — must still pass

### Task 4: Verify acceptance criteria
- [ ] Verify the task resolves latest patch releases correctly (e.g. 1.32 -> v1.32.13, 1.37 -> v1.37.0-alpha.0)
- [ ] Verify swagger.json and v3/ directory are cached in `.cache/schemas/<full-tag>/` (e.g. `.cache/schemas/v1.35.4/swagger.json` and `.cache/schemas/v1.35.4/v3/`)
- [ ] Verify all 6 packages regenerate successfully
- [ ] Verify the verify step runs and passes for each package
- [ ] Run full test suite (unit tests)
- [ ] Run linter — all issues must be fixed

### Task 5: [Final] Update documentation
- [ ] Update CLAUDE.md — add `mise run regenerate-models` to Quick Reference section
- [ ] Add brief docs in the Code Generation section about the new regeneration workflow

## Technical Details

### Release resolution logic
```
For each minor version (e.g. "1.35"):
  1. GET https://api.github.com/repos/kubernetes/kubernetes/releases?per_page=100
  2. Filter releases where tag_name starts with "v1.35."
  3. Sort by semver, pick the latest (e.g. "v1.35.4")
  4. If no stable release found (e.g. v1.37):
     a. GET https://api.github.com/repos/kubernetes/kubernetes/git/refs/tags/v1.37
     b. Parse refs, sort by semver (alpha < beta < rc < stable), pick latest
  5. Return the resolved tag string
```

### Spec download URL patterns
```
# v2 swagger spec
https://raw.githubusercontent.com/kubernetes/kubernetes/{tag}/api/openapi-spec/swagger.json

# v3 per-group spec file listing (to discover filenames)
https://api.github.com/repos/kubernetes/kubernetes/contents/api/openapi-spec/v3?ref={tag}

# v3 individual spec file
https://raw.githubusercontent.com/kubernetes/kubernetes/{tag}/api/openapi-spec/v3/{filename}.json
```
Example tag: `v1.35.4` — ~64 v3 files per version

### Cache directory structure
Cache key is the full release tag (e.g. `v1.32.13`, `v1.37.0-alpha.0`) to ensure a spec refresh when a new patch version is released.
```
.cache/
└── schemas/
    ├── v1.32.13/
    │   ├── swagger.json
    │   └── v3/
    │       ├── api__v1_openapi.json
    │       ├── apis__apps__v1_openapi.json
    │       └── ... (~64 files)
    ├── v1.33.11/
    │   ├── swagger.json
    │   └── v3/
    │       └── ...
    └── ...
```

### mise.toml task configuration
```toml
[env]
K8S_VERSIONS = "1.32,1.33,1.34,1.35,1.36,1.37"

[tasks.regenerate-models]
description = "Download latest K8s OpenAPI specs and regenerate all model packages"
run = "uv run python -m scripts.codegen regenerate --versions $K8S_VERSIONS"
```

## Post-Completion

**Manual verification** (if applicable):
- Run `mise run regenerate-models` on a clean checkout to verify full flow
- Verify on Linux/Windows if possible (the Python script should be platform-agnostic since it uses only stdlib + uv)
- Check that `.cache/schemas/` is properly gitignored

**External system updates** (if applicable):
- Consider adding a CI workflow that runs regeneration periodically (e.g. weekly) to catch new K8s patch releases — out of scope for this task
