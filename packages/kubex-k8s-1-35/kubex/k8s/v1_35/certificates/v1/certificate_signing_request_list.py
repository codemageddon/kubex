from __future__ import annotations

from typing import Literal

from kubex.k8s.v1_35.certificates.v1.certificate_signing_request import (
    CertificateSigningRequest,
)
from kubex_core.models.list_entity import ListEntity
from kubex_core.models.metadata import ListMetadata
from pydantic import Field


class CertificateSigningRequestList(ListEntity[CertificateSigningRequest]):
    """CertificateSigningRequestList is a collection of CertificateSigningRequest objects"""

    api_version: Literal["certificates.k8s.io/v1"] = Field(
        default="certificates.k8s.io/v1",
        alias="apiVersion",
        description="APIVersion defines the versioned schema of this representation of an object. Servers should convert recognized schemas to the latest internal value, and may reject unrecognized values. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#resources",
    )
    items: list[CertificateSigningRequest] = Field(
        ...,
        alias="items",
        description="items is a collection of CertificateSigningRequest objects",
    )
    kind: Literal["CertificateSigningRequestList"] = Field(
        default="CertificateSigningRequestList",
        alias="kind",
        description="Kind is a string value representing the REST resource this object represents. Servers may infer this from the endpoint the client submits requests to. Cannot be updated. In CamelCase. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds",
    )
    metadata: ListMetadata = Field(..., alias="metadata")


CertificateSigningRequest.__RESOURCE_CONFIG__._list_model = (
    CertificateSigningRequestList
)
