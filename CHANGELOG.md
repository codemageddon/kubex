# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- `configure_from_kubeconfig(config_file=...)` loads a specific kubeconfig file, resolving its
  relative paths against it.
- Kubeconfig impersonation (`as`, `as-uid`, `as-groups`, `as-user-extra`), basic auth
  (`username`/`password`), `tls-server-name`, and exec `provideClusterInfo`, with matching
  `ClientConfiguration` arguments (`tls_server_name`, `username`/`password`, `impersonate_*`).
- `KubexConnectionError` and `KubexTimeoutError` (also a `TimeoutError`) for transport failures
  on both backends; `TooManyRequests` (429); `KubexApiError.retry_after`.
- `ExecResult.raise_for_status()` and `ExecError`, exported from `kubex.api`.
- `since_time` for `logs.get()`/`logs.stream()`.
- `kubex_core.models.types`: `Time`, `MicroTime`, `Quantity`, `NullAsEmptyList`,
  `NullAsEmptyDict`.
- `ObjectMetadata.managed_fields`/`self_link` and `ListMetadata.shard_info`.

### Fixed

- Single-object calls reject an empty or `None` name instead of targeting the whole collection;
  names and namespaces are validated and percent-encoded.
- Watches and log streams no longer inherit the client's default read/total timeout.
- httpx watches and log streams split lines only on `\n` (U+0085 in an object broke the
  stream); aiohttp has no line-length cap; non-UTF-8 log output is decoded with replacement.
- `create_client()` picks httpx under trio when aiohttp is also installed.
- Dry-run `delete()`/`delete_collection()`.
- `ApplyPatch` sends `apiVersion`/`kind`, RFC 3339 timestamps and no `managedFields`;
  `metadata.patch()` with `ApplyPatch` targets the resource's kind.
- Scale subresource at 0 replicas.
- Spec-required list, map and timestamp fields accept `null` (EndpointSlice, CSINode and
  events.k8s.io Event lists).
- `CustomResourceDefinition` schema fields (`default`, `enum`, `items`, `additionalProperties`).
- Unknown fields round-trip through resource models instead of being dropped on replace.
- `MicroTime` always serializes six fractional digits; naive datetimes serialize as UTC.
- `Quantity` fields accept numbers.
- Default plurals for custom resources (`Gateway` → `gateways`, `Mesh` → `meshes`).
- A subclass of a resource model gets its own list model.
- `Status` bodies without `metadata` parse.
- `JsonPatch.copy()` on pydantic < 2.11.
- `field_validation` and `version_match` accept plain strings.
- `send_initial_events=True` sets `allowWatchBookmarks`.
- Kubeconfig: entries for other contexts no longer break loading; a scheme-less server
  defaults to `https://`; relative exec commands and `idp-certificate-authority` resolve against
  the kubeconfig directory; `*-data` fields take precedence over file paths.
- In-cluster config with an IPv6 `KUBERNETES_SERVICE_HOST`; a missing namespace file falls back
  to `"default"`.
- Exec credential plugins show their stderr live (interactive and device-code prompts); plugins
  returning client certificates raise a clear `ConfigurationError`.
- OIDC: `client-secret` and `refresh-token` are optional; a valid `id-token` is used until it
  expires.
- Secrets no longer appear in validation errors, kubeconfig YAML errors, logs or reprs
  (including exec `args`, the exec cluster `config`, and `ClientOptions.proxy` credentials, also
  in aiohttp proxy errors).
- `tokenFile` wins over an inline `token`, as in client-go; a failed re-read keeps the last token.
- Temp files for `*-data` credentials are recreated if deleted and removed only by the process
  that created them.
- API errors carry a message, e.g. `404 Not Found: pods "x" not found (reason: NotFound)`.
- WebSocket handshake HTTP errors raise the matching `KubexApiError` subclass.
- httpx: partial pool options keep the default connection limits; a numeric `request_timeout`
  is a total timeout.
- `Warning` headers containing commas.
- Non-ASCII impersonation values on the httpx backend (sent as UTF-8).
- WebSocket keepalive pings on aiohttp; paused exec/attach/portforward sessions are no longer
  closed by httpx-ws ping timeouts.
- Exec/attach/portforward no longer drop output when a consumer falls behind.
- `wait_for_status()`/`run()` wait for the full status instead of resolving on the first empty
  error-channel frame.
- Large stdin and portforward writes are sent in 32 KiB frames.
- `run()` returns an already received status when a later stdin write fails.
- Empty frames are no longer delivered to exec/attach consumers.
- `listen()` closes the local connection when the remote side finishes.
- `kubex` pins `kubex-core` to the same release; `kubex-k8s-*` packages require
  `kubex-core>=0.1.0b4,<0.2`.
- `kubex-core` and `kubex-k8s-*` distributions include the MIT `LICENSE` file.
- Model regeneration keeps each `kubex-k8s-*` package's existing version unless
  `--package-version` is given.

### Changed

- **Breaking:** Transport failures raise `KubexConnectionError`/`KubexTimeoutError` instead of
  httpx/aiohttp exceptions.
- **Breaking:** A kubeconfig context without `namespace` scopes namespace-scoped `Api`s to
  `"default"`, as kubectl does.
- **Breaking:** Invalid kubeconfig content (YAML, schema, missing referenced files, server URL)
  raises `ConfigurationError` instead of `ValidationError`; outside a cluster with no
  kubeconfig, `create_client()` raises `ConfigurationError`.
- **Breaking:** Kubeconfig models are lenient: file paths are `Path` (checked only for the
  selected context), `Cluster.server` is `str | None`, `Context.cluster`/`user` are optional, and
  unknown keys are dropped.
- **Breaking:** Exec/attach/portforward streams apply backpressure: a channel that is enabled
  but never read blocks the session. `stdout_truncated`, `stderr_truncated`,
  `port_data_truncated` and `port_error_truncated` are deprecated and always `False`.
- **Breaking:** Spec-required `Time`/`MicroTime`/byte fields in generated models are typed
  `T | None`. The generated `JSON`/`JSONSchemaPropsOr*`, `ManagedFieldsEntry` and `ShardInfo`
  modules are removed; `ManagedFieldsEntry` and `ShardInfo` live in `kubex_core.models.metadata`.
- Exec plugins without `interactiveMode` run as `IfAvailable`; non-interactive plugins get no
  stdin.
- `ClientConfiguration.url` from a kubeconfig keeps the server URL as written (no trailing
  slash added).
- The httpx backend warns that `tls_server_name` is not applied when connecting through an HTTP
  proxy.
- Failing exec plugins, an OIDC token response without `id_token`, and a missing kubeconfig
  context, cluster or user raise `ConfigurationValueError`, a `ConfigurationError` that is also a
  `ValueError`.

## [0.1.0-beta.3] - 2026-10-23

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
- Preliminary Kubernetes 1.38 support (`kubex-k8s-1-38`).
- Python 3.15 support.

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

- **Breaking:** Python 3.10 is no longer supported; the minimum is now 3.11. The
  `exceptiongroup` dependency is dropped.
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
- `kubex-k8s-1-37` regenerated against the Kubernetes 1.37 release spec.

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

[unreleased]: https://github.com/codemageddon/kubex/compare/v0.1.0-beta.3...HEAD
[0.1.0-beta.3]: https://github.com/codemageddon/kubex/compare/v0.1.0-beta.2...v0.1.0-beta.3
[0.1.0-beta.2]: https://github.com/codemageddon/kubex/compare/v0.1.0-beta.1...v0.1.0-beta.2
[0.1.0-beta.1]: https://github.com/codemageddon/kubex/releases/tag/v0.1.0-beta.1
