from __future__ import annotations

from typing import ClassVar, Literal

from pydantic import Field

from kubex.k8s.v1_35.scheduling.v1alpha1.workload_spec import WorkloadSpec
from kubex_core.models.interfaces import NamespaceScopedEntity
from kubex_core.models.resource_config import ResourceConfig, Scope


class Workload(NamespaceScopedEntity):
    """Workload allows for expressing scheduling constraints that should be used when managing lifecycle of workloads from scheduling perspective, including scheduling, preemption, eviction and other phases."""

    __RESOURCE_CONFIG__: ClassVar[ResourceConfig["Workload"]] = ResourceConfig[
        "Workload"
    ](
        version="v1alpha1",
        kind="Workload",
        group="scheduling.k8s.io",
        plural="workloads",
        scope=Scope.NAMESPACE,
    )
    api_version: Literal["scheduling.k8s.io/v1alpha1"] = Field(
        default="scheduling.k8s.io/v1alpha1",
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
