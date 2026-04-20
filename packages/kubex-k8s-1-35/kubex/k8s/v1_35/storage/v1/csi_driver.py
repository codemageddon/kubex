from __future__ import annotations

from typing import ClassVar, Literal

from pydantic import Field

from kubex.k8s.v1_35.storage.v1.csi_driver_spec import CSIDriverSpec
from kubex_core.models.interfaces import ClusterScopedEntity
from kubex_core.models.resource_config import ResourceConfig, Scope


class CSIDriver(ClusterScopedEntity):
    """CSIDriver captures information about a Container Storage Interface (CSI) volume driver deployed on the cluster. Kubernetes attach detach controller uses this object to determine whether attach is required. Kubelet uses this object to determine whether pod information needs to be passed on mount. CSIDriver objects are non-namespaced."""

    __RESOURCE_CONFIG__: ClassVar[ResourceConfig["CSIDriver"]] = ResourceConfig[
        "CSIDriver"
    ](
        version="v1",
        kind="CSIDriver",
        group="storage.k8s.io",
        plural="csidrivers",
        scope=Scope.CLUSTER,
    )
    api_version: Literal["storage.k8s.io/v1"] = Field(
        default="storage.k8s.io/v1",
        alias="apiVersion",
        description="APIVersion defines the versioned schema of this representation of an object. Servers should convert recognized schemas to the latest internal value, and may reject unrecognized values. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#resources",
    )
    kind: Literal["CSIDriver"] = Field(
        default="CSIDriver",
        alias="kind",
        description="Kind is a string value representing the REST resource this object represents. Servers may infer this from the endpoint the client submits requests to. Cannot be updated. In CamelCase. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds",
    )
    spec: CSIDriverSpec = Field(
        ...,
        alias="spec",
        description="spec represents the specification of the CSI Driver.",
    )
