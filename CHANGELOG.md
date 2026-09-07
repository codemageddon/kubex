# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- `KUBECONFIG` supports an `os.pathsep`-separated list of files, merged with `kubectl`'s
  precedence.
- `configure_from_kubeconfig()` now authenticates via `users[].user.token`/`tokenFile`, `exec`,
  and `oidc` auth-providers (`ExecAuthProvider`/`OIDCAuthProvider`, both credential-refreshing
  and OIDC requiring `https` endpoints), and forwards `namespace` and
  `insecure-skip-tls-verify`.
- `Api`/`create_api()` fall back to `client.configuration.namespace` for namespace-scoped
  resources created without an explicit `namespace=`. `BaseClient` gained a `configuration`
  property.
- `PortForwarder.port_error_truncated` flags a truncated per-port error buffer.

### Fixed

- `allowWatchBookmarks` query parameter handling on watch requests.
- `sendInitialEvents` now pairs with `resourceVersionMatch=NotOlderThan` on watch requests.
- Watch `ERROR` events now raise the correct `KubexApiError` subclass with the full `Status`.
- `api.metadata.watch()` `Accept`/`Content-Type` headers.
- `anyio` is now a runtime dependency.
- `ResourceConfig.__get__` no longer mutates the shared instance inherited by `BaseEntity`
  subclasses without their own `__RESOURCE_CONFIG__`.
- `BaseRefreshableToken`'s concurrency guard fixed (cross-task lock release under concurrent
  callers).
- `AioHttpClient` preserves a path component on the configured server URL.
- `HeadersWrapper.get_all()` on aiohttp no longer raises `KeyError` for an error response
  missing `Content-Type`.
- `MergePatch`/`StrategicMergePatch` default `exclude_none=False`, so an explicit `None` field
  reaches the server as `null`. `ApplyPatch` is unaffected.
- Codegen regeneration removes the previous `kubex/k8s/v1_NN/` module tree before writing.
- `ClientConfiguration.try_refresh_token=False` now pins the token to its first read.
- `ExecAuthProvider` applies the credential plugin's configured `env` entries, preserves its
  stderr on a non-zero exit, and reports its `expirationTimestamp`.
- `handle_request_error()` no longer raises `UnicodeDecodeError` on a non-UTF-8 error body.
- A 500 response now raises `KubernetesError` instead of a bare `KubexApiError`.
- `AioHttpClient.stream_lines()` strips line terminators, matching the httpx backend.
- Exec/OIDC credential expiry now derives from the plugin's/id_token's reported expiry instead
  of a fixed 60-second cadence.

### Changed

- **Breaking:** In-cluster `Api`/`create_api()` calls without an explicit `namespace=` now
  scope to the pod's own namespace. `ClientConfiguration(namespace=...)` no longer defaults to
  `"default"`.
- **Breaking:** `WatchEvent`, `EventType`, and `Bookmark` moved from
  `kubex_core.models.watch_event` to `kubex.core.watch_event`.
- **Breaking:** `VersionMatch.NOT_EXACT` renamed to `VersionMatch.NOT_OLDER_THAN`.
- **Breaking:** Fixed typos in public names: `ConfgiurationError` → `ConfigurationError`,
  `ClientChoise` → `ClientChoice`, `get_version_and_froup_from_api_version` →
  `get_version_and_group_from_api_version`.
- **Breaking:** `resource_version` removed from `RequestBuilder.watch()` and
  `MetadataRequestBuilder.watch_metadata()` — pass it on `WatchOptions` instead.
- `create()`/`replace()` and the subresource `replace()` methods no longer pass
  `exclude_unset=True` to `model_dump_json()`; fields left at their Python-side default are now
  included on the wire.

## [0.1.0-beta.2] - 2026-05-12

### Added

- `ClientOptions.trust_env: bool = False` — opt-in to environment-driven HTTP proxy
  configuration (`HTTP_PROXY`, `HTTPS_PROXY`, `ALL_PROXY`, `NO_PROXY`) and netrc-based
  proxy credentials on both backends. Netrc is used for proxy credentials only; kubex's
  per-request bearer `Authorization` header always wins over any netrc-derived target-host
  Basic auth.

### Changed

- The httpx backend now passes `trust_env=False` to `httpx.AsyncClient` by default,
  overriding httpx's own library default of `True`. Users who relied on httpx silently
  honoring `HTTP_PROXY` / `HTTPS_PROXY` / `NO_PROXY` must opt in explicitly with
  `ClientOptions(trust_env=True)`. This aligns httpx behavior with aiohttp, which has
  always defaulted to `trust_env=False`.

## [0.1.0-beta.1] - 2026-05-06

Initial public beta release.

### Added

- Async-first `Api[ResourceType]` client with type-safe CRUD, watch, and three patch types (`MergePatch`, `StrategicMergePatch`, `JsonPatch`).
- Pluggable HTTP backends: `HttpxClient` and `AioHttpClient`. Async-runtime agnostic — supports asyncio and trio.
- Descriptor-based subresource APIs: `logs`, `status`, `scale`, `eviction`, `ephemeral_containers`, `resize`, `exec`, `attach`, `portforward`, `metadata`.
- Configuration loading from kubeconfig files and in-cluster pod environment, with exec-provider and refreshable-token authentication.
- OpenAPI → Pydantic v2 code generator and pre-generated workspace packages for Kubernetes 1.32–1.37.
- MkDocs documentation site, examples, and a benchmark suite against `kubernetes-asyncio`.

[unreleased]: https://github.com/codemageddon/kubex/compare/v0.1.0-beta.2...HEAD
[0.1.0-beta.2]: https://github.com/codemageddon/kubex/compare/v0.1.0-beta.1...v0.1.0-beta.2
[0.1.0-beta.1]: https://github.com/codemageddon/kubex/releases/tag/v0.1.0-beta.1
