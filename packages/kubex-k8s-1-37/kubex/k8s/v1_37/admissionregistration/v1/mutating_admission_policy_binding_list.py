from __future__ import annotations

from typing import Literal

from kubex.k8s.v1_37.admissionregistration.v1.mutating_admission_policy_binding import (
    MutatingAdmissionPolicyBinding,
)
from kubex_core.models.list_entity import ListEntity
from kubex_core.models.metadata import ListMetadata
from pydantic import Field


class MutatingAdmissionPolicyBindingList(ListEntity[MutatingAdmissionPolicyBinding]):
    """MutatingAdmissionPolicyBindingList is a list of MutatingAdmissionPolicyBinding."""

    api_version: Literal["admissionregistration.k8s.io/v1"] = Field(
        default="admissionregistration.k8s.io/v1",
        alias="apiVersion",
        description="APIVersion defines the versioned schema of this representation of an object. Servers should convert recognized schemas to the latest internal value, and may reject unrecognized values. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#resources",
    )
    items: list[MutatingAdmissionPolicyBinding] = Field(
        ..., alias="items", description="List of PolicyBinding."
    )
    kind: Literal["MutatingAdmissionPolicyBindingList"] = Field(
        default="MutatingAdmissionPolicyBindingList",
        alias="kind",
        description="Kind is a string value representing the REST resource this object represents. Servers may infer this from the endpoint the client submits requests to. Cannot be updated. In CamelCase. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds",
    )
    metadata: ListMetadata = Field(
        ...,
        alias="metadata",
        description="metadata is the standard list metadata. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds",
    )


MutatingAdmissionPolicyBinding.__RESOURCE_CONFIG__._list_model = (
    MutatingAdmissionPolicyBindingList
)
