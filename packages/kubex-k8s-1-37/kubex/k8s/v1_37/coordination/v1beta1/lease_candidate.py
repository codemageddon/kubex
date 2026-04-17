from __future__ import annotations

from typing import ClassVar, Literal

from kubex.k8s.v1_37.coordination.v1beta1.lease_candidate_spec import LeaseCandidateSpec
from kubex_core.models.interfaces import ClusterScopedEntity
from kubex_core.models.resource_config import ResourceConfig, Scope
from pydantic import Field


class LeaseCandidate(ClusterScopedEntity):
    """LeaseCandidate defines a candidate for a Lease object. Candidates are created such that coordinated leader election will pick the best leader from the list of candidates."""

    __RESOURCE_CONFIG__: ClassVar[ResourceConfig["LeaseCandidate"]] = ResourceConfig[
        "LeaseCandidate"
    ](
        version="v1beta1",
        kind="LeaseCandidate",
        group="coordination.k8s.io",
        plural="leasecandidates",
        scope=Scope.CLUSTER,
    )
    api_version: Literal["coordination.k8s.io/v1beta1"] = Field(
        default="coordination.k8s.io/v1beta1",
        alias="apiVersion",
        description="APIVersion defines the versioned schema of this representation of an object. Servers should convert recognized schemas to the latest internal value, and may reject unrecognized values. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#resources",
    )
    kind: Literal["LeaseCandidate"] = Field(
        default="LeaseCandidate",
        alias="kind",
        description="Kind is a string value representing the REST resource this object represents. Servers may infer this from the endpoint the client submits requests to. Cannot be updated. In CamelCase. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds",
    )
    spec: LeaseCandidateSpec = Field(
        ...,
        alias="spec",
        description="spec contains the specification of the Lease. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#spec-and-status",
    )
