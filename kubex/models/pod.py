from __future__ import annotations

from typing import Any, ClassVar, Literal

from kubex.models.interfaces import (
    Evictable,
    HasLogs,
    HasStatusSubresource,
    NamespaceScopedEntity,
)
from kubex.models.resource_config import (
    ResourceConfig,
    Scope,
)


class Pod(NamespaceScopedEntity, HasLogs, Evictable, HasStatusSubresource):
    """Pod is a collection of containers that can run on a host."""

    __RESOURCE_CONFIG__: ClassVar[ResourceConfig[Pod]] = ResourceConfig["Pod"](
        version="v1",
        kind="Pod",
        group="core",
        plural="pods",
        scope=Scope.NAMESPACE,
    )

    api_version: Literal["v1"] = "v1"
    kind: Literal["Pod"] = "Pod"
    spec: dict[str, Any] | None = None
    status: dict[str, Any] | None = None
