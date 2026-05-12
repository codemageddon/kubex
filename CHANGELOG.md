# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
