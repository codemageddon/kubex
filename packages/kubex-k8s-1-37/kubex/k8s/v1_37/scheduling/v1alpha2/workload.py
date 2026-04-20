from __future__ import annotations

from typing import ClassVar, Literal

from pydantic import Field

from kubex.k8s.v1_37.scheduling.v1alpha2.workload_spec import WorkloadSpec
from kubex_core.models.interfaces import NamespaceScopedEntity
from kubex_core.models.resource_config import ResourceConfig, Scope


class Workload(NamespaceScopedEntity):
    """Workload allows for expressing scheduling constraints that should be used when managing the lifecycle of workloads from the scheduling perspective, including scheduling, preemption, eviction and other phases. Workload API enablement is toggled by the GenericWorkload feature gate."""

    __RESOURCE_CONFIG__: ClassVar[ResourceConfig["Workload"]] = ResourceConfig[
        "Workload"
    ](
        version="v1alpha2",
        kind="Workload",
        group="scheduling.k8s.io",
        plural="workloads",
        scope=Scope.NAMESPACE,
    )
    api_version: Literal["scheduling.k8s.io/v1alpha2"] = Field(
        default="scheduling.k8s.io/v1alpha2",
        alias="apiVersion",
        description="APIVersion defines the versioned schema of this representation of an object. Servers should convert recognized schemas to the latest internal value, and may reject unrecognized values. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#resources",
    )
    kind: Literal["Workload"] = Field(
        default="Workload",
        alias="kind",
        description="Kind is a string value representing the REST resource this object represents. Servers may infer this from the endpoint the client submits requests to. Cannot be updated. In CamelCase. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds",
    )
    spec: WorkloadSpec = Field(
        ...,
        alias="spec",
        description="Spec defines the desired behavior of a Workload.",
    )
