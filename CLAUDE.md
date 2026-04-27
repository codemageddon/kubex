# CLAUDE.md

## Project Overview

Kubex is an async-first Kubernetes client library for Python, inspired by [kube.rs](https://kube.rs/). It is built on Pydantic v2 and is async-runtime agnostic (supports asyncio and trio). The project is in **alpha** (v0.1.0-alpha.1) — backward compatibility may break between releases.

## Quick Reference

```bash
# Install dependencies (requires uv)
uv lock --python 3.13 && uv sync --python 3.13 --all-extras

# Run tests (requires Docker for testcontainers/K3S)
uv run pytest .

# Lint
uv run ruff check .

# Format check
uv run ruff format --check .

# Auto-fix lint + format
uv run ruff check --fix . && uv run ruff format .

# Type check (strict mode)
uv run mypy .

# Run pre-commit hooks
pre-commit run --all-files

# Regenerate all K8s model packages (downloads specs + runs codegen + verifies)
mise run regenerate-models
```

## Repository Structure

```
kubex/                          # Main package — PEP 420 namespace package (no __init__.py) so the
                                #   workspace `kubex-k8s-*` packages can contribute `kubex.k8s.*` submodules.
                                #   Public API is imported from explicit submodules:
                                #   `from kubex.api import Api, create_api`,
                                #   `from kubex.client import BaseClient, create_client`,
                                #   `from kubex.configuration import ClientConfiguration`
├── __version__.py              # Version string (0.1.0-alpha.1)
├── py.typed                    # PEP 561 type hint marker
├── api/                        # High-level API layer
│   ├── api.py                  # Api[ResourceType] generic class + create_api() factory
│   ├── _logs.py                # LogsAccessor + _LogsDescriptor — api.logs.get() and api.logs.stream()
│   ├── _scale.py               # ScaleAccessor + _ScaleDescriptor — api.scale.get(), replace(), patch()
│   ├── _status.py              # StatusAccessor + _StatusDescriptor — api.status.get(), replace(), patch()
│   ├── _eviction.py            # EvictionAccessor + _EvictionDescriptor — api.eviction.create()
│   ├── _ephemeral_containers.py # EphemeralContainersAccessor + _EphemeralContainersDescriptor — api.ephemeral_containers.get(), replace(), patch()
│   ├── _resize.py              # ResizeAccessor + _ResizeDescriptor — api.resize.get(), replace(), patch()
│   ├── _exec.py                # ExecAccessor + _ExecDescriptor + ExecResult — api.exec.run(), api.exec.stream()
│   ├── _attach.py              # AttachAccessor + _AttachDescriptor — api.attach.stream() (no run(); attaches to existing container process)
│   ├── _stream_session.py      # StreamSession — multiplexes Kubernetes channel-protocol streams over WebSocketConnection (used by exec and attach)
│   ├── _metadata.py            # MetadataAccessor — api.metadata.get(), list(), patch(), watch()
│   └── _protocol.py            # ApiProtocol[ResourceType], type aliases, SubresourceNotAvailable, namespace helpers
├── client/                     # HTTP client implementations
│   ├── client.py               # BaseClient ABC, create_client() factory, ClientChoise enum
│   ├── websocket.py            # WebSocketConnection ABC — abstraction used by exec and attach subresources
│   ├── httpx.py                # HttpxClient implementation (exec via httpx-ws)
│   └── aiohttp.py              # AioHttpClient implementation (exec via aiohttp ws_connect)
├── configuration/              # Auth and cluster config
│   ├── configuration.py        # ClientConfiguration, KubeConfig pydantic models
│   ├── file_config.py          # configure_from_kubeconfig() — kubeconfig file parsing
│   ├── incluster_config.py     # configure_from_pod_env() — in-cluster service account auth
│   └── auth/                   # Authentication mechanisms
│       ├── exec.py             # Exec provider authentication
│       ├── oidc.py             # OIDC provider (in progress)
│       └── refreshable_token.py # Token refresh logic
└── core/                       # Request/response primitives
    ├── exceptions.py           # Exception hierarchy (KubexException → KubexApiError → HTTP-specific)
    ├── request.py              # Request dataclass — `query_params: dict[str, str]` for the standard case;
                                #   `query_param_pairs: list[tuple[str, str]]` for repeated keys (e.g. exec `command=` entries),
                                #   forwarded as-is by both http clients in `connect_websocket()` when set
    ├── response.py             # Response dataclass + HeadersWrapper
    ├── params.py               # API option classes (ListOptions, GetOptions, DeleteOptions, ExecOptions, AttachOptions, etc.)
                                #   + Timeout, TimeoutTypes — HTTP timeout configuration
    ├── json_patch.py           # JSON Patch RFC 6902 operation models (JsonPatchAdd, etc.) + JsonPatch RootModel
    ├── json_pointer.py         # JSON Pointer RFC 6901 implementation (JsonPointer custom str type)
    ├── patch.py                # Patch protocol + ApplyPatch, MergePatch, StrategicMergePatch
                                #   Re-exports JsonPatch models and JsonPointer from json_patch/json_pointer
    ├── subresource.py          # Subresource definitions
    ├── exec_channels.py        # Exec WebSocket channel protocol (V5ChannelProtocol, channel ID constants, select_protocol())
    └── request_builder/        # Constructs HTTP requests from API calls
        ├── builder.py          # RequestBuilder (main builder composing mixins)
        ├── constants.py        # HTTP headers and MIME types
        ├── metadata.py         # Metadata request building
        ├── subresource.py      # Subresource request building
        ├── logs.py             # Log streaming request building
        ├── exec.py             # Exec WebSocket upgrade request building (repeated command= query params)
        └── attach.py           # Attach WebSocket upgrade request building (mirrors exec.py, no command= params)

packages/                       # Workspace packages
├── kubex-core/                 # Shared base models and types (kubex_core)
│   └── kubex_core/models/
│       ├── base.py             # BaseK8sModel — Pydantic base with camelCase alias
│       ├── base_entity.py      # BaseEntity — base for all K8s resources (__RESOURCE_CONFIG__)
│       ├── interfaces.py       # Marker classes: ClusterScopedEntity, NamespaceScopedEntity, HasLogs, Evictable, HasEphemeralContainers, HasResize, etc.
│       ├── resource_config.py  # ResourceConfig[T] descriptor — kind, version, scope, URL generation
│       ├── metadata.py         # ObjectMetadata, ListMetadata, OwnerReference
│       ├── typing.py           # ResourceType TypeVar
│       ├── list_entity.py      # ListEntity[ResourceType] wrapper
│       ├── watch_event.py      # WatchEvent[ResourceType] and EventType enum
│       ├── status.py           # Status response model
│       ├── scale.py            # Scale subresource model
│       ├── eviction.py         # Eviction subresource model (policy/v1)
│       └── partial_object_meta.py # Partial metadata variant
└── kubex-k8s-{1-32..1-37}/     # Generated Kubernetes resource models (one package per K8s version)
    └── kubex/k8s/v1_NN/        # ~666 generated model files across ~30 API groups
        ├── core/v1/            # Pod, Namespace, Service, ConfigMap, Secret, etc.
        ├── apps/v1/            # Deployment, StatefulSet, DaemonSet, ReplicaSet
        ├── batch/v1/           # Job, CronJob
        ├── networking/v1/      # Ingress, NetworkPolicy
        ├── rbac/v1/            # Role, ClusterRole, RoleBinding, ClusterRoleBinding
        └── ...                 # All other API groups for that K8s version

scripts/codegen/                # OpenAPI → Pydantic v2 code generator
├── __main__.py                 # Typer CLI: generate, verify, regenerate commands
├── spec_loader.py              # OpenAPI/Swagger JSON parsing
├── fetch_specs.py              # GitHub API client for resolving K8s releases and downloading OpenAPI specs
├── resource_detector.py        # Identifies K8s resources from spec
├── type_mapper.py              # OpenAPI type → Python type mapping
├── model_emitter.py            # Generates Pydantic model code
├── enum_emitter.py             # Generates enum definitions
├── ir.py                       # Intermediate representation of models
├── naming.py                   # Python naming conventions
├── package_builder.py          # Writes generated package to disk
├── ref_resolver.py             # Resolves $ref links in OpenAPI spec
├── templates/                  # Jinja2 templates for code generation
└── tests/                      # Codegen tests: golden snapshots, resource detection, spec fetching, regenerate CLI

test/                           # Test suite
├── e2e/                        # End-to-end tests (testcontainers + K3S)
│   ├── conftest.py             # Fixtures: K3S container, client fixtures, temp namespace
│   ├── test_core_api_pod.py    # Pod CRUD tests
│   ├── test_core_api_namespaces.py  # Namespace listing tests
│   ├── test_subresource_apis.py # E2E tests for Status, Eviction, EphemeralContainers, Resize subresources
│   ├── test_exec.py            # E2E tests for Pod exec subresource (run + stream against K3S)
│   └── test_attach.py          # E2E tests for Pod attach subresource (stream against K3S)
├── test_configuration/         # Unit tests for configuration and auth
│   ├── test_file_config.py     # Kubeconfig file parsing tests
│   ├── test_incluster_config.py # In-cluster configuration tests
│   └── auth/
│       ├── test_exec_provider.py # Exec provider unit tests
│       └── test_refreshable_token.py # Token refresh and async lock tests
├── test_error_handling.py      # handle_request_error() and exception hierarchy tests
├── test_metadata_accessor.py   # MetadataAccessor (get, list, patch) tests
├── test_models/                # Unit tests for kubex-core models
│   └── test_eviction.py        # Eviction model tests
├── test_patch/                 # Unit tests for patch models
│   ├── test_json_patch.py      # JSON Patch operation model tests
│   └── test_json_pointer.py    # JSON Pointer (RFC 6901) tests
├── test_request_builder/       # Unit tests for request builder methods
│   ├── test_builder.py         # Core RequestBuilder methods (get, list, create, delete, replace, patch, watch)
│   ├── test_create_subresource.py # create_subresource() method tests
│   ├── test_logs.py            # LogsRequestBuilder (logs, stream_logs) tests
│   ├── test_metadata.py        # MetadataRequestBuilder (get/list/watch/patch_metadata) tests
│   ├── test_subresource.py     # SubresourceRequestBuilder (get/replace/patch_subresource) tests
│   ├── test_exec.py            # ExecRequestBuilder (exec_request URL + repeated command= params) tests
│   └── test_attach.py          # AttachRequestBuilder (attach_request URL + query_param_pairs) tests
├── test_exec/                  # Unit tests for exec subresource (ExecOptions, channel protocol, ExecAccessor)
├── test_attach/                # Unit tests for attach subresource (AttachOptions, AttachAccessor)
├── test_stream/                # Unit tests for StreamSession channel multiplexer (shared by exec and attach)
├── test_client/                # Unit tests for client WebSocket layer (BaseClient ABC, AioHttpClient, HttpxClient)
├── test_subresource_descriptors/ # Unit tests for descriptor-based subresource APIs
└── test_timeout/               # Unit tests for HTTP timeout settings

examples/                       # Usage examples
├── get_pod.py                  # Create, get, list metadata, delete a Pod
├── watch_pods.py               # Watch for Pod events
├── get_pod_logs.py             # Stream Pod logs
├── list_namespaces.py          # List cluster namespaces
├── patch_deployment.py         # All three patch types (MergePatch, StrategicMergePatch, JsonPatch)
├── replace_pod.py              # Get → modify → replace pattern
├── scale_deployment.py         # Scale subresource (get + replace)
├── status_operations.py        # Status subresource (get + replace)
├── error_handling.py           # Exception handling (KubexApiError, NotFound, Conflict)
├── aiohttp_client.py           # Using AioHttpClient explicitly
├── exec_pod.py                 # Pod exec subresource — api.exec.run() + api.exec.stream() interactive shell
├── attach_pod.py               # Pod attach subresource — api.attach.stream() with stdin/stdout
└── delete_collection.py        # Bulk delete with label_selector

.github/workflows/
├── lint.yaml                   # Pre-commit, ruff check, ruff format --check, mypy, codegen verify
├── test.yaml                   # pytest with all extras on Python 3.13
├── publish-test.yaml           # Build + publish to Test PyPI on PRs (OIDC trusted publishing)
└── publish.yaml                # Build + publish to production PyPI on v* tag push (OIDC trusted publishing)
```

## Build System & Dependencies

- **Package manager**: [uv](https://github.com/astral-sh/uv) with workspace support
- **Build backend**: hatchling
- **Python**: 3.10, 3.11, 3.12, 3.13, 3.14
- **Workspace members**: `packages/*` (kubex-core, kubex-k8s-1-32 through kubex-k8s-1-37)
- **Core deps**: `pydantic>=2.0,<3`, `pyyaml>=6.0.2`, `kubex-core` (workspace), `exceptiongroup>=1.2` (Python <3.11 only — used by `StreamSession.__aexit__` to unwrap single-exception `BaseExceptionGroup`s from the anyio task-group cleanup)
- **Optional deps** (install via `--all-extras` or individually):
  - `httpx>=0.27.2` — primary HTTP client
  - `httpx-ws>=0.7` — WebSocket support for the httpx client (required for `exec` and `attach`); install via the dedicated `httpx-ws` extra (`kubex[httpx-ws]`), which also pulls in `httpx`. The plain `httpx` extra deliberately omits it so non-WebSocket installs stay slim.
  - `aiohttp>=3.11.2` — alternative HTTP client (built-in WebSocket support via `ws_connect`)
- **Dev deps** include `kubex-k8s-1-35` (workspace, used for tests), `jinja2`, `typer` (for codegen), testing/linting tools
- **Version** is stored in `kubex/__version__.py` and referenced from `pyproject.toml` via hatch

## Code Quality Tools

| Tool | Config | Purpose |
|------|--------|---------|
| **ruff** | `pyproject.toml` (default rules) | Linting and formatting |
| **mypy** | `pyproject.toml` — `strict = true`, `pydantic.mypy` plugin | Static type checking |
| **pre-commit** | `.pre-commit-config.yaml` | Git hooks: YAML check, trailing whitespace, EOF fixer, ruff lint+format |
| **pytest** | default config | Test runner with anyio backend support |

## Key Architecture Patterns

### Generics for type safety
The central `Api[ResourceType]` class is generic over the Kubernetes resource type. This enables type-safe CRUD operations:
```python
from kubex.k8s.v1_35.core.v1.pod import Pod

api: Api[Pod] = Api(Pod, client=client)
pod: Pod = await api.get("my-pod", namespace="default")
```

### Resource configuration via descriptor
Each resource model declares a `__RESOURCE_CONFIG__` class variable (a `ResourceConfig` descriptor) that provides metadata: API version, kind, plural name, scope, and URL generation. The descriptor auto-populates missing fields from model field defaults.

### Pydantic models with camelCase aliases
All models inherit from `BaseK8sModel` which uses `alias_generator=to_camel` and `populate_by_name=True`. This means Python code uses `snake_case` while JSON serialization uses `camelCase` to match the Kubernetes API.

### Pluggable HTTP clients
`BaseClient` is an ABC. Implementations (`HttpxClient`, `AioHttpClient`) are lazily imported. The `create_client()` factory auto-detects which library is installed (prefers httpx). `BaseClient` also exposes `connect_websocket(request, subprotocols)` returning a `WebSocketConnection` (defined in `kubex/client/websocket.py`); the default raises `NotImplementedError`. `HttpxClient` implements it via `httpx-ws` (lazy import — raises `ConfgiurationError` if missing); `AioHttpClient` uses aiohttp's built-in `ws_connect`. Both adapters prefer `Request.query_param_pairs` over `Request.query_params` when building the upgrade URL so exec's repeated `command=` entries are preserved.

### Configuration auto-loading
`create_client()` → tries kubeconfig file first → falls back to in-cluster pod environment.

### Ellipsis sentinel for optional overrides
`Ellipsis` (`...`) is used as a sentinel to distinguish "not provided" (use the default) from `None` (explicitly disabled). This pattern is used in two places:
- **Namespace**: `...` = use the `Api` instance default; `None` = explicitly no namespace.
- **Request timeout**: `...` = use the client-level default (or the HTTP library default if none was configured); `None` = explicitly disable timeouts for this call.

### Exception hierarchy
```
KubexException
├── ConfgiurationError
└── KubexClientException
    └── KubexApiError[C]  (generic over str | Status)
        ├── BadRequest
        ├── Unauthorized
        ├── Forbidden
        ├── NotFound
        ├── MethodNotAllowed
        ├── Conflict
        ├── Gone
        └── UnprocessableEntity
```

### Descriptor-based subresource APIs
Subresource capabilities (logs, scale, status, eviction, ephemeral_containers, resize, exec, attach) use Python non-data descriptors with `__get__` overloads to provide type-safe access. Each capability is a class variable on `Api` (e.g., `logs = _LogsDescriptor()`) that returns a typed accessor (`LogsAccessor[T]`) when `T` has the matching marker interface, or raises `NotImplementedError` at runtime (and resolves to `SubresourceNotAvailable` for type checkers) when it does not. Accessors are cached on the instance after first access via `instance.__dict__` (the standard non-data descriptor caching pattern), so repeated attribute access returns the same object without re-invoking the descriptor. Accessor objects receive individual components (client, request_builder, namespace, scope, resource_type) rather than a back-reference to `Api`. Metadata uses the same accessor pattern (`MetadataAccessor`) but is always available (no descriptor guard needed) and is created eagerly in `Api.__init__`. The `exec` and `attach` accessors are built on a WebSocket channel-multiplexing layer (`kubex/core/exec_channels.py` + `kubex/api/_stream_session.py`) that uses the v5 channel protocol (`v5.channel.k8s.io`). `StreamSession` exposes `stdin` (writer with `write()` / `close()`), `stdout` and `stderr` as `MemoryObjectReceiveStream[bytes]` async iterators (max-buffer 128 frames each), `resize(width=, height=)`, `close_stdin()`, and `await wait_for_status() -> Status | None` (resolves to `None` if the connection closes before any error frame arrives). Concurrent writes are serialised through an internal `anyio.Lock` so resize and stdin frames cannot interleave on the wire. Exiting a `StreamSession` context manager cancels the read loop's task group before closing the underlying WebSocket, so callers can leave `stream()` early without deadlocking even when the server is still holding the connection open. `close_stdin()` is idempotent. When `tty=True` is requested the kubelet merges stderr into stdout and does not open the stderr channel, so `session.stderr` closes immediately. `run(name, command=, stdin=None)` does not open a stdin channel; `run(..., stdin=b"")` opens, writes zero bytes, and immediately closes one. `ExecResult.exit_code` returns `0` for `Status.status == "Success"`, the integer parsed from `status.details.causes` (where `reason == "ExitCode"`) for a non-zero exit, and `None` when status is missing or carries no recognisable exit information — `None` therefore does not imply success. Exec WebSocket failures (handshake errors, abnormal close, timeout) surface as `KubexClientException`; missing `httpx-ws` raises `ConfgiurationError`. The `attach` accessor exposes only `stream()` (no `run()`) — it opens a bidirectional channel to a container's existing stdin/stdout/stderr without issuing a new command; the same `StreamSession` semantics apply (TTY merging, `wait_for_status()`, etc.).
```python
pod_api: Api[Pod] = Api(Pod, client=client, namespace="default")
await pod_api.logs.get("my-pod")        # OK: Pod has HasLogs
await pod_api.scale.get("my-pod")       # type error + runtime NotImplementedError

deploy_api: Api[Deployment] = Api(Deployment, client=client, namespace="default")
await deploy_api.scale.get("my-deploy") # OK: Deployment has HasScaleSubresource
```

### Marker interfaces for resource capabilities
Resources declare capabilities via multiple inheritance from marker classes: `NamespaceScopedEntity`, `ClusterScopedEntity`, `HasLogs`, `HasStatusSubresource`, `HasScaleSubresource`, `Evictable`, `HasEphemeralContainers`, `HasResize`, `HasAttach`, `HasExec`, `HasPortForward`.

## Testing

- **Framework**: pytest with `pytest-cov` and `anyio` for async support
- **E2E tests** use `testcontainers` with a K3S container (requires Docker); located in `test/e2e/`
- **Unit tests** for request builder methods in `test/test_request_builder/`, error handling in `test/test_error_handling.py`, metadata accessor in `test/test_metadata_accessor.py`, configuration/auth in `test/test_configuration/`, timeout settings in `test/test_timeout/`, patch models in `test/test_patch/`, subresource descriptors in `test/test_subresource_descriptors/`
- **Codegen tests** with golden snapshots in `scripts/codegen/tests/`
- E2E tests are parameterized over both HTTP clients (`httpx`, `aiohttp`) and async backends (`asyncio`, `trio` — trio only with httpx)
- Mark async tests with `@pytest.mark.anyio`
- The `conftest.py` provides session-scoped K3S cluster, per-test client fixtures, and a temporary namespace fixture that creates/cleans up namespaces

## CI/CD

Four GitHub Actions workflows:

**Lint** (`lint.yaml`) — runs on push and pull_request:
1. Pre-commit hooks (all files)
2. `ruff check .`
3. `ruff format --check .`
4. `mypy .` (strict, with all extras installed)
5. Verify generated packages — runs `python -m scripts.codegen verify` for each `packages/kubex-k8s-*`

**Test** (`test.yaml`) — runs on push and pull_request:
1. `pytest .` on Python 3.13 with all extras

**Publish Test** (`publish-test.yaml`) — runs on pull requests to `main`:
1. Appends `.devN` version suffix to all 8 packages
2. Builds all packages in dependency order
3. Publishes to Test PyPI using OIDC trusted publishing
4. Posts a PR comment with Test PyPI links
- Uses GitHub environment `test-pypi`; skips publish for fork PRs

**Publish** (`publish.yaml`) — runs on `v*` tag push:
1. Verifies all 8 package versions match the tag
2. Builds all packages in dependency order
3. Publishes to production PyPI using OIDC trusted publishing
- Uses GitHub environment `pypi`

## Releasing

To publish a new version to PyPI:

1. Bump the version in `kubex/__version__.py` and in every `packages/*/pyproject.toml` — all 8 packages must have the same version string
2. Commit and push to `main`
3. Create and push a git tag matching the version: `git tag v<VERSION> && git push origin v<VERSION>`
4. The `publish.yaml` workflow will verify version consistency, build all packages, and publish to production PyPI

Both publish workflows use PyPI OIDC trusted publishing — no API tokens are stored in the repository. Each of the 8 packages must have a trusted publisher configured in its PyPI (and Test PyPI) project settings. See the comment block at the top of each workflow file for the exact configuration values.

## Coding Conventions

- **Type annotations everywhere** — mypy strict mode is enforced
- **`from __future__ import annotations`** — used in most modules for PEP 604 union syntax
- **snake_case** for all Python identifiers; camelCase only in Pydantic alias output
- **Private modules** prefixed with underscore (e.g., `_logs.py`, `_metadata.py`, `_protocol.py`)
- **`ClassVar`** for resource configuration on model classes
- **`Literal` types** for `api_version` and `kind` fields on resource models
- **Async context managers** for client lifecycle (`async with client:`)
- **`match`/`case` statements** used for dispatching (e.g., client selection, error handling)
- **Protocols** used for structural typing (e.g., `Patch` protocol in `core/patch.py`)
- **No synchronous API** — all client operations are async

## Code Generation

Kubernetes resource models are generated from the official OpenAPI spec using a built-in code generator at `scripts/codegen/`. Generated packages live under `packages/` (e.g., `kubex-k8s-1-32`).

```bash
# Generate models for a Kubernetes version (requires a local swagger.json)
uv run python -m scripts.codegen generate --swagger <path-to-swagger.json> --k8s-version 1.35

# Verify generated package passes mypy
uv run python -m scripts.codegen verify packages/kubex-k8s-1-35
```

Generated models are fully typed with proper spec/status fields (not generic dicts), inherit from `kubex-core` base classes, and include marker interfaces (`HasStatusSubresource`, `HasLogs`, etc.) based on the resource's API capabilities. They are importable as:
```python
from kubex.k8s.v1_35.core.v1.pod import Pod
from kubex.k8s.v1_35.core.v1.namespace import Namespace
from kubex.k8s.v1_35.apps.v1.deployment import Deployment
```

### Regenerating all model packages

Use `mise run regenerate-models` to automatically resolve the latest patch/pre-release tag for each configured Kubernetes minor version, download both v2 and v3 OpenAPI specs from the Kubernetes GitHub repo, regenerate all `kubex-k8s-*` packages, and verify them with mypy. Downloaded specs are cached in `.cache/schemas/<tag>/` and reused on subsequent runs. The list of minor versions is configured via `K8S_VERSIONS` in `mise.toml`.

```bash
# Regenerate all packages (uses versions from mise.toml)
mise run regenerate-models

# Or invoke the CLI directly with custom versions
uv run python -m scripts.codegen regenerate --versions 1.35,1.36
```

### Adding support for a new Kubernetes version

1. Run the codegen: `uv run python -m scripts.codegen generate --swagger <path-to-swagger.json> --k8s-version <VERSION>`
2. Add `kubex-k8s-<VERSION> = { workspace = true }` to `[tool.uv.sources]` in `pyproject.toml`
3. Add `"k8s-<VERSION>" = ["kubex-k8s-<VERSION>"]` to `[project.optional-dependencies]` in `pyproject.toml`
4. Verify with `uv run python -m scripts.codegen verify packages/kubex-k8s-<VERSION>`

## Known Quirks

- `ConfgiurationError` has a typo in the class name (in `core/exceptions.py`)
- `ClientChoise` has a typo (in `client/client.py`)
- `get_version_and_froup_from_api_version` has a typo in the function name (in `resource_config.py`)
- These are existing in the codebase — do not "fix" them without explicit request, as they are part of the public API
