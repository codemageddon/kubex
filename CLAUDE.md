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
```

## Repository Structure

```
kubex/                          # Main package
├── __init__.py                 # Public API: Api, create_api, BaseClient, create_client, ClientConfiguration
├── __version__.py              # Version string (0.1.0-alpha.1)
├── py.typed                    # PEP 561 type hint marker
├── api/                        # High-level API layer
│   ├── api.py                  # Api[ResourceType] generic class + create_api() factory
│   ├── _logs.py                # LogsMixin — logs() and stream_logs()
│   ├── _metadata.py            # MetadataMixin — get_metadata() and list_metadata()
│   ├── _subressource.py        # Subresource operations
│   └── _protocol.py            # ApiProtocol[ResourceType] and type aliases
├── client/                     # HTTP client implementations
│   ├── client.py               # BaseClient ABC, create_client() factory, ClientChoise enum
│   ├── httpx.py                # HttpxClient implementation
│   └── aiohttp.py              # AioHttpClient implementation
├── configuration/              # Auth and cluster config
│   ├── configuration.py        # ClientConfiguration, KubeConfig pydantic models
│   ├── file_config.py          # configure_from_kubeconfig() — kubeconfig file parsing
│   └── incluster_config.py     # configure_from_pod_env() — in-cluster service account auth
├── core/                       # Request/response primitives
│   ├── exceptions.py           # Exception hierarchy (KubexException → KubexApiError → HTTP-specific)
│   ├── request.py              # Request dataclass
│   ├── response.py             # Response dataclass + HeadersWrapper
│   ├── params.py               # API option classes (ListOptions, GetOptions, DeleteOptions, etc.)
│   ├── patch.py                # Patch protocols (ApplyPatch, MergePatch, StrategicMergePatch, JsonPatch)
│   ├── subresource.py          # Subresource definitions
│   └── request_builder/        # Constructs HTTP requests from API calls
│       ├── builder.py          # RequestBuilder (main builder composing mixins)
│       ├── constants.py        # HTTP headers and MIME types
│       ├── metadata.py         # Metadata request building
│       ├── subresource.py      # Subresource request building
│       └── logs.py             # Log streaming request building
└── models/                     # Kubernetes resource models
    ├── base.py                 # BaseK8sModel — Pydantic base with camelCase alias
    ├── base_entity.py          # BaseEntity — base for all K8s resources (__RESOURCE_CONFIG__)
    ├── interfaces.py           # Marker classes: ClusterScopedEntity, NamespaceScopedEntity, HasLogs, etc.
    ├── resource_config.py      # ResourceConfig[T] descriptor — kind, version, scope, URL generation
    ├── metadata.py             # ObjectMetadata, ListMetadata, OwnerReference
    ├── typing.py               # ResourceType TypeVar
    ├── pod.py                  # Pod model
    ├── namespace.py            # Namespace model
    ├── list_entity.py          # ListEntity[ResourceType] wrapper
    ├── watch_event.py          # WatchEvent[ResourceType] and EventType enum
    ├── status.py               # Status response model
    ├── scale.py                # Scale subresource model
    └── partial_object_meta.py  # Partial metadata variant

test/                           # Test suite
└── e2e/                        # End-to-end tests (testcontainers + K3S)
    ├── conftest.py             # Fixtures: K3S container, client fixtures, temp namespace
    ├── test_core_api_pod.py    # Pod CRUD tests
    └── test_core_api_namespaces.py  # Namespace listing tests

examples/                       # Usage examples
├── get_pod.py                  # Create, get, list metadata, delete a Pod
├── watch_pods.py               # Watch for Pod events
├── get_pod_logs.py             # Stream Pod logs
└── list_namespaces.py          # List cluster namespaces

.github/workflows/
├── lint.yaml                   # Pre-commit, ruff check, ruff format --check, mypy
└── test.yaml                   # pytest with all extras on Python 3.13
```

## Build System & Dependencies

- **Package manager**: [uv](https://github.com/astral-sh/uv)
- **Build backend**: hatchling
- **Python**: 3.10, 3.11, 3.12, 3.13
- **Core deps**: `pydantic>=2.0,<3`, `pyyaml>=6.0.2`
- **Optional deps** (install via `--all-extras` or individually):
  - `httpx>=0.27.2` — primary HTTP client
  - `aiohttp>=3.11.2` — alternative HTTP client
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
api: Api[Pod] = Api(Pod, client=client)
pod: Pod = await api.get("my-pod", namespace="default")
```

### Resource configuration via descriptor
Each resource model declares a `__RESOURCE_CONFIG__` class variable (a `ResourceConfig` descriptor) that provides metadata: API version, kind, plural name, scope, and URL generation. The descriptor auto-populates missing fields from model field defaults.

### Pydantic models with camelCase aliases
All models inherit from `BaseK8sModel` which uses `alias_generator=to_camel` and `populate_by_name=True`. This means Python code uses `snake_case` while JSON serialization uses `camelCase` to match the Kubernetes API.

### Pluggable HTTP clients
`BaseClient` is an ABC. Implementations (`HttpxClient`, `AioHttpClient`) are lazily imported. The `create_client()` factory auto-detects which library is installed (prefers httpx).

### Configuration auto-loading
`create_client()` → tries kubeconfig file first → falls back to in-cluster pod environment.

### Namespace handling with Ellipsis sentinel
`Ellipsis` (`...`) is used as a sentinel to distinguish "not provided" (use the default) from `None` (explicitly no namespace). This allows setting a default namespace on the `Api` instance while still overriding per-call.

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

### Marker interfaces for resource capabilities
Resources declare capabilities via multiple inheritance from marker classes: `NamespaceScopedEntity`, `ClusterScopedEntity`, `HasLogs`, `HasStatusSubresource`, `HasScaleSubresource`, `Evictable`.

## Testing

- **Framework**: pytest with `pytest-cov` and `anyio` for async support
- **E2E tests** use `testcontainers` with a K3S container (requires Docker)
- Tests are parameterized over both HTTP clients (`httpx`, `aiohttp`) and async backends (`asyncio`, `trio` — trio only with httpx)
- Test files are in `test/e2e/`
- Mark async tests with `@pytest.mark.anyio`
- The `conftest.py` provides session-scoped K3S cluster, per-test client fixtures, and a temporary namespace fixture that creates/cleans up namespaces

## CI/CD

Two GitHub Actions workflows run on push and pull_request:

**Lint** (`lint.yaml`):
1. Pre-commit hooks (all files)
2. `ruff check .`
3. `ruff format --check .`
4. `mypy .` (strict, with all extras installed)

**Test** (`test.yaml`):
1. `pytest .` on Python 3.13 with all extras

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

## Adding a New Kubernetes Resource

1. Create a new file in `kubex/models/` (e.g., `deployment.py`)
2. Define the model inheriting from appropriate interfaces:
   ```python
   class Deployment(NamespaceScopedEntity, HasStatusSubresource, HasScaleSubresource):
       __RESOURCE_CONFIG__: ClassVar[ResourceConfig["Deployment"]] = ResourceConfig(
           version="v1", kind="Deployment", group="apps",
           plural="deployments", scope=Scope.NAMESPACE,
       )
       api_version: Literal["apps/v1"] = "apps/v1"
       kind: Literal["Deployment"] = "Deployment"
       spec: dict[str, Any] | None = None
       status: dict[str, Any] | None = None
   ```
3. The `Api[Deployment]` class will automatically work with the new resource type

## Known Quirks

- `ConfgiurationError` has a typo in the class name (in `core/exceptions.py`)
- `ClientChoise` has a typo (in `client/client.py`)
- `_subressource.py` has a typo in the filename
- `get_version_and_froup_from_api_version` has a typo in the function name (in `resource_config.py`)
- These are existing in the codebase — do not "fix" them without explicit request, as they are part of the public API
