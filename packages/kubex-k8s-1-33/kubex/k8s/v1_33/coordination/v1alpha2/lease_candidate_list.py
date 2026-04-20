from __future__ import annotations

from typing import Literal

from pydantic import Field

from kubex.k8s.v1_33.coordination.v1alpha2.lease_candidate import LeaseCandidate
from kubex_core.models.list_entity import ListEntity
from kubex_core.models.metadata import ListMetadata


class LeaseCandidateList(ListEntity[LeaseCandidate]):
    """LeaseCandidateList is a list of Lease objects."""

    api_version: Literal["coordination.k8s.io/v1alpha2"] = Field(
        default="coordination.k8s.io/v1alpha2",
        alias="apiVersion",
        description="APIVersion defines the versioned schema of this representation of an object. Servers should convert recognized schemas to the latest internal value, and may reject unrecognized values. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#resources",
    )
    items: list[LeaseCandidate] = Field(
        ..., alias="items", description="items is a list of schema objects."
    )
    kind: Literal["LeaseCandidateList"] = Field(
        default="LeaseCandidateList",
        alias="kind",
        description="Kind is a string value representing the REST resource this object represents. Servers may infer this from the endpoint the client submits requests to. Cannot be updated. In CamelCase. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds",
    )
    metadata: ListMetadata = Field(
        ...,
        alias="metadata",
        description="Standard list metadata. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#metadata",
    )


LeaseCandidate.__RESOURCE_CONFIG__._list_model = LeaseCandidateList
