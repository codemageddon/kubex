# Operations

This section covers the full set of operations you can perform on Kubernetes resources with Kubex. Read the [Concepts](../concepts/index.md) section first if you are new to the library.

<div class="grid cards" markdown>

- :material-database-edit: **[CRUD](crud.md)**

    `get`, `list`, `create`, `replace`, `delete`, and `delete_collection` — the core Kubernetes resource lifecycle operations with filtering, pagination, and deletion options.

- :material-eye: **[Watch](watch.md)**

    Long-lived `watch()` streams, `WatchEvent` and `EventType`, bookmark events, the `sendInitialEvents` pattern, and the restart-on-410-Gone recipe.

- :material-file-edit: **[Patch](patch.md)**

    All three patch strategies: `MergePatch`, `StrategicMergePatch`, and `JsonPatch` (RFC 6902) with its fluent builder API and JSON Pointer paths.

- :material-timer: **[Timeouts](timeouts.md)**

    `Timeout`, `TimeoutTypes`, client-level vs per-call configuration, the Ellipsis sentinel, and guidance for long-lived watch streams.

</div>
