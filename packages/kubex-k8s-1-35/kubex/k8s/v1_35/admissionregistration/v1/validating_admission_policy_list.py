from __future__ import annotations

from typing import Literal

from pydantic import Field

from kubex.k8s.v1_35.admissionregistration.v1.validating_admission_policy import (
    ValidatingAdmissionPolicy,
)
from kubex_core.models.list_entity import ListEntity
from kubex_core.models.metadata import ListMetadata


class ValidatingAdmissionPolicyList(ListEntity[ValidatingAdmissionPolicy]):
    """ValidatingAdmissionPolicyList is a list of ValidatingAdmissionPolicy."""

    api_version: Literal["admissionregistration.k8s.io/v1"] = Field(
        default="admissionregistration.k8s.io/v1",
        alias="apiVersion",
        description="APIVersion defines the versioned schema of this representation of an object. Servers should convert recognized schemas to the latest internal value, and may reject unrecognized values. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#resources",
    )
    items: list[ValidatingAdmissionPolicy] = Field(
        ..., alias="items", description="List of ValidatingAdmissionPolicy."
    )
    kind: Literal["ValidatingAdmissionPolicyList"] = Field(
        default="ValidatingAdmissionPolicyList",
        alias="kind",
        description="Kind is a string value representing the REST resource this object represents. Servers may infer this from the endpoint the client submits requests to. Cannot be updated. In CamelCase. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds",
    )
    metadata: ListMetadata = Field(
        ...,
        alias="metadata",
        description="Standard list metadata. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds",
    )


ValidatingAdmissionPolicy.__RESOURCE_CONFIG__._list_model = (
    ValidatingAdmissionPolicyList
)
