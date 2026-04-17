from __future__ import annotations

from typing import ClassVar, Literal

from kubex.k8s.v1_30.core.v1.node_status import NodeStatus
from kubex_core.models.interfaces import ClusterScopedEntity, HasStatusSubresource
from kubex_core.models.resource_config import ResourceConfig, Scope
from pydantic import Field


class Node(ClusterScopedEntity, HasStatusSubresource):
    """Node is a worker node in Kubernetes."""

    __RESOURCE_CONFIG__: ClassVar[ResourceConfig["Node"]] = ResourceConfig["Node"](
        version="v1",
        kind="Node",
        group="core",
        plural="nodes",
        scope=Scope.CLUSTER,
    )
    api_version: Literal["v1"] = Field(default="v1", alias="apiVersion")
    kind: Literal["Node"] = Field(default="Node", alias="kind")
    status: NodeStatus | None = Field(default=None, alias="status")
