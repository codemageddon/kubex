from __future__ import annotations

from typing import Literal

from kubex.k8s.v1_36.certificates.v1beta1.pod_certificate_request import (
    PodCertificateRequest,
)
from kubex_core.models.list_entity import ListEntity
from kubex_core.models.metadata import ListMetadata
from pydantic import Field


class PodCertificateRequestList(ListEntity[PodCertificateRequest]):
    """PodCertificateRequestList is a collection of PodCertificateRequest objects"""

    api_version: Literal["certificates.k8s.io/v1beta1"] = Field(
        default="certificates.k8s.io/v1beta1",
        alias="apiVersion",
        description="APIVersion defines the versioned schema of this representation of an object. Servers should convert recognized schemas to the latest internal value, and may reject unrecognized values. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#resources",
    )
    items: list[PodCertificateRequest] = Field(
        ...,
        alias="items",
        description="items is a collection of PodCertificateRequest objects",
    )
    kind: Literal["PodCertificateRequestList"] = Field(
        default="PodCertificateRequestList",
        alias="kind",
        description="Kind is a string value representing the REST resource this object represents. Servers may infer this from the endpoint the client submits requests to. Cannot be updated. In CamelCase. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds",
    )
    metadata: ListMetadata = Field(
        ..., alias="metadata", description="metadata contains the list metadata."
    )


PodCertificateRequest.__RESOURCE_CONFIG__._list_model = PodCertificateRequestList
