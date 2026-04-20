from __future__ import annotations

from typing import Literal

from pydantic import Field

from kubex.k8s.v1_32.admissionregistration.v1.validating_admission_policy_binding import (
    ValidatingAdmissionPolicyBinding,
)
from kubex_core.models.list_entity import ListEntity
from kubex_core.models.metadata import ListMetadata


class ValidatingAdmissionPolicyBindingList(
    ListEntity[ValidatingAdmissionPolicyBinding]
):
    """ValidatingAdmissionPolicyBindingList is a list of ValidatingAdmissionPolicyBinding."""

    api_version: Literal["admissionregistration.k8s.io/v1"] = Field(
        default="admissionregistration.k8s.io/v1",
        alias="apiVersion",
        description="APIVersion defines the versioned schema of this representation of an object. Servers should convert recognized schemas to the latest internal value, and may reject unrecognized values. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#resources",
    )
    items: list[ValidatingAdmissionPolicyBinding] = Field(
        ..., alias="items", description="List of PolicyBinding."
    )
    kind: Literal["ValidatingAdmissionPolicyBindingList"] = Field(
        default="ValidatingAdmissionPolicyBindingList",
        alias="kind",
        description="Kind is a string value representing the REST resource this object represents. Servers may infer this from the endpoint the client submits requests to. Cannot be updated. In CamelCase. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds",
    )
    metadata: ListMetadata = Field(
        ...,
        alias="metadata",
        description="Standard list metadata. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds",
    )


ValidatingAdmissionPolicyBinding.__RESOURCE_CONFIG__._list_model = (
    ValidatingAdmissionPolicyBindingList
)
