from typing import Any, ClassVar, Literal

from kubex.models.base import (
    HasStatusSubresource,
    NamespaceScopedEntity,
    NamespaceScopedMetadata,
    PodProtocol,
    ResourceConfig,
    Scope,
)


class Pod(NamespaceScopedEntity, PodProtocol, HasStatusSubresource):
    """Pod is a collection of containers that can run on a host."""

    __RESOURCE_CONFIG__: ClassVar[ResourceConfig] = ResourceConfig(
        version="v1",
        kind="Pod",
        group="core",
        plural="pods",
        scope=Scope.NAMESPACE,
    )

    api_version: Literal["v1"] = "v1"
    kind: Literal["Pod"] = "Pod"
    metadata: NamespaceScopedMetadata
    spec: dict[str, Any] | None = None
    status: dict[str, Any] | None = None
