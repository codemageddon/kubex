# kubex-core

Shared foundation types for [Kubex](https://github.com/codemageddon/kubex) and its generated Kubernetes resource packages (`kubex-k8s-*`).

Contains:

- `kubex_core.models.base.BaseK8sModel` — Pydantic base with camelCase aliasing.
- `kubex_core.models.base_entity.BaseEntity` — base class for all K8s resources.
- `kubex_core.models.interfaces` — marker interfaces (`NamespaceScopedEntity`, `ClusterScopedEntity`, `HasLogs`, `HasStatusSubresource`, `HasScaleSubresource`, `Evictable`).
- `kubex_core.models.resource_config` — `ResourceConfig` descriptor + `Scope`.
- `kubex_core.models.metadata` — `ObjectMetadata`, `ListMetadata`, `OwnerReference`.
- `kubex_core.models.watch_event`, `list_entity`, `partial_object_meta`, `status`, `scale`.

This package is a runtime dependency of the `kubex` client and every generated resource package. End users generally install `kubex` + one `kubex-k8s-*` of choice; this package is pulled in transitively.
