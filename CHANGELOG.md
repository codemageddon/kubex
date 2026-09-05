# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed

- `allowWatchBookmarks` query parameter handling on watch requests.
- `WatchOptions`: `sendInitialEvents` (whether `true` or `false`) now always pairs with
  `resourceVersionMatch=NotOlderThan` on the outgoing request, matching the Kubernetes API's
  `validateWatchOptions` requirement.
- Watch `ERROR` events. It now raises the correct `KubexApiError` subclass, with the full
  `Status` — including `message` and `details` — preserved as its content.
- `api.metadata.watch()` sent `Accept`/`Content-Type` fixed.
- `anyio` is now a runtime dependency instead of a dev-only one.

### Changed

- **Breaking:** `WatchEvent`, `EventType`, and `Bookmark` moved from
  `kubex_core.models.watch_event` (the separately published `kubex-core` package) to
  `kubex.core.watch_event`. Import from the new location; no compatibility re-export is
  provided.
- **Breaking:** `VersionMatch.NOT_EXACT` renamed to `VersionMatch.NOT_OLDER_THAN` (the enum
  value is unchanged, `"NotOlderThan"`).
- **Breaking:** fixed three typos in public names, with no compatibility
  aliases: `ConfgiurationError` → `ConfigurationError` (`kubex.core.exceptions`),
  `ClientChoise` → `ClientChoice` (`kubex.client.client`), and
  `get_version_and_froup_from_api_version` → `get_version_and_group_from_api_version`
  (`kubex_core.models.resource_config`).
- **Breaking:** `resource_version` removed from `RequestBuilder.watch()` and
  `MetadataRequestBuilder.watch_metadata()` — pass it on `WatchOptions` instead.
- `create()`/`replace()` and the subresource `replace()` methods (`scale`, `status`, `eviction`,
  `resize`, `ephemeral_containers`) no longer pass `exclude_unset=True` to `model_dump_json()`.
  Fields left at their Python-side default are now included on the wire. This has no effect on
  the generated `kubex-k8s-*`/`kubex_core` models, whose optional fields default to `None` and
  are still dropped by `exclude_none=True`; for user-defined CRD models with non-`None` field
  defaults, a `replace()` can now write that default back to the cluster for a field the caller
  never touched.

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
