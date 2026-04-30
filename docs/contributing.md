# Contributing to Kubex

This page covers local documentation preview, strict builds, link checking, versioned deploys, and maintainer-only workflows.

## Prerequisites

Install the docs dependency group:

```bash
uv sync --group docs
```

This installs `mkdocs`, `mkdocs-material`, `mkdocstrings[python]`, `mike`, and `pymdown-extensions` into your project virtualenv.

## Local preview

Start a live-reload server:

```bash
mise run docs:serve
```

The site is served at `http://127.0.0.1:8000/`. Changes to any file under `docs/` or to `mkdocs.yml` are reflected immediately without restarting.

## Strict build

Validate the entire site with `--strict` mode (warnings become errors):

```bash
mise run docs:build
```

This is the same command CI runs. It catches broken internal links, unresolved `mkdocstrings` references, and misconfigured nav entries. The output is written to `site/` (git-ignored).

**Run this before opening a PR** — a clean strict build is required to merge docs changes.

## Link checking

Check external links with [lychee](https://github.com/lycheeverse/lychee):

```bash
# Offline (checks internal links only)
lychee --offline docs/

# Full external check
lychee --config lychee.toml docs/
```

CI runs the full external check on every push and pull request (via `lycheeverse/lychee-action`). The `lychee.toml` at the repo root configures retries, accepted status codes, and exclusions for example-only URLs such as `localhost` and `kubernetes.default.svc`.

## Writing docs

- Pages live under `docs/` and are plain Markdown with [Material for MkDocs](https://squidfunk.github.io/mkdocs-material/) extensions.
- Code blocks use triple-backtick fences with a language tag (`python`, `bash`, `yaml`, etc.).
- Admonitions use the `!!! note` / `!!! warning` / `!!! tip` syntax.
- Tabbed blocks use `=== "Tab"` syntax from `pymdownx.tabbed`.
- API reference uses `:::module.path` directives rendered by `mkdocstrings`.

## Versioned deploys with mike

[mike](https://github.com/jimporter/mike) manages per-release version directories on the `gh-pages` branch. Each deployment is a subdirectory (`0.1.0-beta.1/`, `dev/`, etc.) with a `versions.json` index that powers the Material version selector.

### Deploy commands

```bash
# Deploy the current docs as a tagged release (no alias change)
uv run --group docs mike deploy --push 0.2.0

# Deploy the current docs to the rolling 'dev' channel
uv run --group docs mike deploy --push --update-aliases dev

# Promote a release to the 'latest' alias (manual — see warning below)
uv run --group docs mike alias --push 0.2.0 latest

# Set the default version (what users land on at the root URL)
uv run --group docs mike set-default --push latest

# List all deployed versions
uv run --group docs mike list
```

All `--push` variants require push access to the repository. Omit `--push` to test locally against a temporary branch.

### CI deploy workflow

`.github/workflows/docs.yaml` handles automated deploys:

- **Push to `main`** → `mike deploy dev` (updates the rolling development channel)
- **Push a `v*` tag** → `mike deploy <version>` only (publishes the versioned site, does *not* touch `latest`)
- **`workflow_dispatch`** → deploys the `dev` channel (or a custom version via workflow input)

The workflow uses the same `astral-sh/setup-uv` + `uv sync --group docs` pattern as the lint and test workflows.

!!! warning "Promotion to `latest` is manual"
    The tag deploy intentionally does *not* update the `latest` alias or
    `set-default`. If kubex ever ships parallel release lines (e.g., v1.x
    patches alongside v2.x), an automatic promotion would let a v1 patch tag
    silently demote v2 to "old" — users landing on the docs root would see the
    wrong major version.

    After tagging, verify the release is the project's newest line, then
    promote manually from your maintainer machine:

    ```bash
    uv run --group docs mike alias --push <version> latest
    uv run --group docs mike set-default --push latest
    ```

## First-time bootstrap

The `gh-pages` branch must exist before the CI deploy workflow can run `mike set-default`. Seed it from a maintainer's machine:

```bash
# Clone a fresh copy or use your existing checkout
git fetch origin

# Deploy the initial release — this creates the gh-pages branch if it does not exist
uv run --group docs mike deploy --push --update-aliases 0.1.0-beta.1 latest

# Confirm the version list
uv run --group docs mike list
```

After this first push:

1. Go to the repository's **Settings → Pages** and set **Source = Deploy from a branch**, **Branch = `gh-pages`**, **Folder = `/ (root)`**.
2. Set **Custom domain = `kubex.codemageddon.me`** and tick **Enforce HTTPS**. GitHub will write a root-level `CNAME` file on the `gh-pages` branch automatically; `mike` preserves root-level files across subsequent deploys.

If GitHub does not write the `CNAME` automatically, add it manually:

```bash
git checkout gh-pages
echo 'kubex.codemageddon.me' > CNAME
git add CNAME && git commit -m "set custom domain" && git push
git checkout -
```

## Maintainer: regenerating K8s models

!!! note "Maintainer-only"
    This section is relevant only when updating or adding Kubernetes API version support. It is not needed for normal documentation contributions.

Kubernetes resource models under `packages/kubex-k8s-*/` are generated from the official OpenAPI spec. To regenerate:

```bash
# Regenerate all configured K8s versions (downloads specs, runs codegen, verifies with mypy)
mise run regenerate-models
```

The list of minor versions is configured via `K8S_VERSIONS` in `mise.toml`. Downloaded specs are cached in `.cache/schemas/<tag>/`.

To regenerate a single version manually:

```bash
# Generate from a local swagger.json
uv run python -m scripts.codegen generate --swagger path/to/swagger.json --k8s-version 1.36

# Verify the generated package type-checks
uv run python -m scripts.codegen verify packages/kubex-k8s-1-36
```

After adding a new K8s version, update `pyproject.toml` to add it to `[tool.uv.sources]` and `[project.optional-dependencies]` — see `CLAUDE.md` for the full checklist.
