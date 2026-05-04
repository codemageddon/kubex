# Concepts

This section explains the core design patterns behind Kubex. Read these pages to understand *why* the library is structured the way it is before diving into the operation and subresource guides.

<div class="grid cards" markdown>

- :material-code-braces: **[Api\[T\]](api.md)**

    The generic `Api[ResourceType]` class, namespace vs cluster scope, the Ellipsis sentinel, and the `create_api()` factory.

- :material-transit-connection-variant: **[Clients](clients.md)**

    `BaseClient` ABC, `create_client()` auto-detection, and the difference between `HttpxClient` and `AioHttpClient`.

- :material-cog: **[Configuration](configuration.md)**

    `ClientConfiguration`, auto-loading from kubeconfig or in-cluster pod environment, and exec credential providers.

- :material-source-branch: **[Subresources](subresources.md)**

    The descriptor pattern, marker interfaces (`HasLogs`, `HasExec`, …), and how mypy enforces subresource availability at compile time.

- :material-alert-circle: **[Exceptions](exceptions.md)**

    The full exception hierarchy from `KubexException` down to HTTP-specific errors like `NotFound` and `Conflict`.

</div>
