from __future__ import annotations

from typing import ClassVar, Literal

from pydantic import Field

from kubex.k8s.v1_35.resource.v1.device_class_spec import DeviceClassSpec
from kubex_core.models.interfaces import ClusterScopedEntity
from kubex_core.models.resource_config import ResourceConfig, Scope


class DeviceClass(ClusterScopedEntity):
    """DeviceClass is a vendor- or admin-provided resource that contains device configuration and selectors. It can be referenced in the device requests of a claim to apply these presets. Cluster scoped. This is an alpha type and requires enabling the DynamicResourceAllocation feature gate."""

    __RESOURCE_CONFIG__: ClassVar[ResourceConfig["DeviceClass"]] = ResourceConfig[
        "DeviceClass"
    ](
        version="v1",
        kind="DeviceClass",
        group="resource.k8s.io",
        plural="deviceclasses",
        scope=Scope.CLUSTER,
    )
    api_version: Literal["resource.k8s.io/v1"] = Field(
        default="resource.k8s.io/v1",
        alias="apiVersion",
        description="APIVersion defines the versioned schema of this representation of an object. Servers should convert recognized schemas to the latest internal value, and may reject unrecognized values. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#resources",
    )
    kind: Literal["DeviceClass"] = Field(
        default="DeviceClass",
        alias="kind",
        description="Kind is a string value representing the REST resource this object represents. Servers may infer this from the endpoint the client submits requests to. Cannot be updated. In CamelCase. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds",
    )
    spec: DeviceClassSpec = Field(
        ...,
        alias="spec",
        description="Spec defines what can be allocated and how to configure it. This is mutable. Consumers have to be prepared for classes changing at any time, either because they get updated or replaced. Claim allocations are done once based on whatever was set in classes at the time of allocation. Changing the spec automatically increments the metadata.generation number.",
    )
