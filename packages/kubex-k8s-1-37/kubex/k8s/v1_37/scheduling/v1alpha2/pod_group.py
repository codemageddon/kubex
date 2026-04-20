from __future__ import annotations

from typing import ClassVar, Literal

from pydantic import Field

from kubex.k8s.v1_37.scheduling.v1alpha2.pod_group_spec import PodGroupSpec
from kubex.k8s.v1_37.scheduling.v1alpha2.pod_group_status import PodGroupStatus
from kubex_core.models.interfaces import HasStatusSubresource, NamespaceScopedEntity
from kubex_core.models.resource_config import ResourceConfig, Scope


class PodGroup(NamespaceScopedEntity, HasStatusSubresource):
    """PodGroup represents a runtime instance of pods grouped together. PodGroups are created by workload controllers (Job, LWS, JobSet, etc...) from Workload.podGroupTemplates. PodGroup API enablement is toggled by the GenericWorkload feature gate."""

    __RESOURCE_CONFIG__: ClassVar[ResourceConfig["PodGroup"]] = ResourceConfig[
        "PodGroup"
    ](
        version="v1alpha2",
        kind="PodGroup",
        group="scheduling.k8s.io",
        plural="podgroups",
        scope=Scope.NAMESPACE,
    )
    api_version: Literal["scheduling.k8s.io/v1alpha2"] = Field(
        default="scheduling.k8s.io/v1alpha2",
        alias="apiVersion",
        description="APIVersion defines the versioned schema of this representation of an object. Servers should convert recognized schemas to the latest internal value, and may reject unrecognized values. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#resources",
    )
    kind: Literal["PodGroup"] = Field(
        default="PodGroup",
        alias="kind",
        description="Kind is a string value representing the REST resource this object represents. Servers may infer this from the endpoint the client submits requests to. Cannot be updated. In CamelCase. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds",
    )
    spec: PodGroupSpec = Field(
        ..., alias="spec", description="Spec defines the desired state of the PodGroup."
    )
    status: PodGroupStatus | None = Field(
        default=None,
        alias="status",
        description="Status represents the current observed state of the PodGroup.",
    )
