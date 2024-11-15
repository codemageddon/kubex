from __future__ import annotations

from typing import Any, ClassVar, Literal

from kubex.models.interfaces import ClusterScopedEntity, HasStatusSubresource
from kubex.models.resource_config import (
    ResourceConfig,
    Scope,
)


class Namespace(ClusterScopedEntity, HasStatusSubresource):
    __RESOURCE_CONFIG__: ClassVar[ResourceConfig[Namespace]] = ResourceConfig[
        "Namespace"
    ](
        version="v1",
        kind="Namespace",
        group="core",
        plural="namespaces",
        scope=Scope.CLUSTER,
    )

    api_version: Literal["v1"] | None = "v1"
    kind: Literal["Namespace"] | None = "Namespace"
    spec: dict[str, Any] | None = None
    status: dict[str, Any] | None = None
