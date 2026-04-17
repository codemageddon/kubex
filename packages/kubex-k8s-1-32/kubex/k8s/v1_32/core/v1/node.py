from __future__ import annotations

from typing import ClassVar, Literal

from kubex.k8s.v1_32.core.v1.node_spec import NodeSpec
from kubex.k8s.v1_32.core.v1.node_status import NodeStatus
from kubex_core.models.interfaces import ClusterScopedEntity, HasStatusSubresource
from kubex_core.models.resource_config import ResourceConfig, Scope
from pydantic import Field


class Node(ClusterScopedEntity, HasStatusSubresource):
    """Node is a worker node in Kubernetes. Each node will have a unique identifier in the cache (i.e. in etcd)."""

    __RESOURCE_CONFIG__: ClassVar[ResourceConfig["Node"]] = ResourceConfig["Node"](
        version="v1",
        kind="Node",
        group="core",
        plural="nodes",
        scope=Scope.CLUSTER,
    )
    api_version: Literal["v1"] = Field(
        default="v1",
        alias="apiVersion",
        description="APIVersion defines the versioned schema of this representation of an object. Servers should convert recognized schemas to the latest internal value, and may reject unrecognized values. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#resources",
    )
    kind: Literal["Node"] = Field(
        default="Node",
        alias="kind",
        description="Kind is a string value representing the REST resource this object represents. Servers may infer this from the endpoint the client submits requests to. Cannot be updated. In CamelCase. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds",
    )
    spec: NodeSpec | None = Field(
        default=None,
        alias="spec",
        description="Spec defines the behavior of a node. https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#spec-and-status",
    )
    status: NodeStatus | None = Field(
        default=None,
        alias="status",
        description="Most recently observed status of the node. Populated by the system. Read-only. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#spec-and-status",
    )
