from typing import Any, ClassVar, Literal

from kubex.models.base import (
    ClusterScopedEntity,
    HasStatusSubresource,
    ResourceConfig,
    Scope,
)


class Namespace(ClusterScopedEntity, HasStatusSubresource):
    __RESOURCE_CONFIG__: ClassVar[ResourceConfig] = ResourceConfig(
        version="v1",
        kind="Namespace",
        group="core",
        plural="namespaces",
        scope=Scope.CLUSTER,
    )

    api_version: Literal["v1"] = "v1"
    kind: Literal["Namespace"] = "Namespace"
    spec: dict[str, Any] | None = None
    status: dict[str, Any] | None = None
