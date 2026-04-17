from __future__ import annotations

from typing import ClassVar, Literal

from kubex.k8s.v1_34.storage.v1.csi_node_spec import CSINodeSpec
from kubex_core.models.interfaces import ClusterScopedEntity
from kubex_core.models.resource_config import ResourceConfig, Scope
from pydantic import Field


class CSINode(ClusterScopedEntity):
    """CSINode holds information about all CSI drivers installed on a node. CSI drivers do not need to create the CSINode object directly. As long as they use the node-driver-registrar sidecar container, the kubelet will automatically populate the CSINode object for the CSI driver as part of kubelet plugin registration. CSINode has the same name as a node. If the object is missing, it means either there are no CSI Drivers available on the node, or the Kubelet version is low enough that it doesn't create this object. CSINode has an OwnerReference that points to the corresponding node object."""

    __RESOURCE_CONFIG__: ClassVar[ResourceConfig["CSINode"]] = ResourceConfig[
        "CSINode"
    ](
        version="v1",
        kind="CSINode",
        group="storage.k8s.io",
        plural="csinodes",
        scope=Scope.CLUSTER,
    )
    api_version: Literal["storage.k8s.io/v1"] = Field(
        default="storage.k8s.io/v1",
        alias="apiVersion",
        description="APIVersion defines the versioned schema of this representation of an object. Servers should convert recognized schemas to the latest internal value, and may reject unrecognized values. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#resources",
    )
    kind: Literal["CSINode"] = Field(
        default="CSINode",
        alias="kind",
        description="Kind is a string value representing the REST resource this object represents. Servers may infer this from the endpoint the client submits requests to. Cannot be updated. In CamelCase. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds",
    )
    spec: CSINodeSpec = Field(
        ..., alias="spec", description="spec is the specification of CSINode"
    )
