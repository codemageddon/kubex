from __future__ import annotations

from typing import ClassVar, Literal

from pydantic import Field

from kubex.k8s.v1_35.resource.v1alpha3.device_taint_rule_spec import DeviceTaintRuleSpec
from kubex.k8s.v1_35.resource.v1alpha3.device_taint_rule_status import (
    DeviceTaintRuleStatus,
)
from kubex_core.models.interfaces import ClusterScopedEntity, HasStatusSubresource
from kubex_core.models.resource_config import ResourceConfig, Scope


class DeviceTaintRule(ClusterScopedEntity, HasStatusSubresource):
    """DeviceTaintRule adds one taint to all devices which match the selector. This has the same effect as if the taint was specified directly in the ResourceSlice by the DRA driver."""

    __RESOURCE_CONFIG__: ClassVar[ResourceConfig["DeviceTaintRule"]] = ResourceConfig[
        "DeviceTaintRule"
    ](
        version="v1alpha3",
        kind="DeviceTaintRule",
        group="resource.k8s.io",
        plural="devicetaintrules",
        scope=Scope.CLUSTER,
    )
    api_version: Literal["resource.k8s.io/v1alpha3"] = Field(
        default="resource.k8s.io/v1alpha3",
        alias="apiVersion",
        description="APIVersion defines the versioned schema of this representation of an object. Servers should convert recognized schemas to the latest internal value, and may reject unrecognized values. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#resources",
    )
    kind: Literal["DeviceTaintRule"] = Field(
        default="DeviceTaintRule",
        alias="kind",
        description="Kind is a string value representing the REST resource this object represents. Servers may infer this from the endpoint the client submits requests to. Cannot be updated. In CamelCase. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds",
    )
    spec: DeviceTaintRuleSpec = Field(
        ...,
        alias="spec",
        description="Spec specifies the selector and one taint. Changing the spec automatically increments the metadata.generation number.",
    )
    status: DeviceTaintRuleStatus | None = Field(
        default=None,
        alias="status",
        description="Status provides information about what was requested in the spec.",
    )
