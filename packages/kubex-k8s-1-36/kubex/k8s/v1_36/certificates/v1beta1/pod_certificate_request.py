from __future__ import annotations

from typing import ClassVar, Literal

from pydantic import Field

from kubex.k8s.v1_36.certificates.v1beta1.pod_certificate_request_spec import (
    PodCertificateRequestSpec,
)
from kubex.k8s.v1_36.certificates.v1beta1.pod_certificate_request_status import (
    PodCertificateRequestStatus,
)
from kubex_core.models.interfaces import HasStatusSubresource, NamespaceScopedEntity
from kubex_core.models.resource_config import ResourceConfig, Scope


class PodCertificateRequest(NamespaceScopedEntity, HasStatusSubresource):
    """PodCertificateRequest encodes a pod requesting a certificate from a given signer. Kubelets use this API to implement podCertificate projected volumes"""

    __RESOURCE_CONFIG__: ClassVar[ResourceConfig["PodCertificateRequest"]] = (
        ResourceConfig["PodCertificateRequest"](
            version="v1beta1",
            kind="PodCertificateRequest",
            group="certificates.k8s.io",
            plural="podcertificaterequests",
            scope=Scope.NAMESPACE,
        )
    )
    api_version: Literal["certificates.k8s.io/v1beta1"] = Field(
        default="certificates.k8s.io/v1beta1",
        alias="apiVersion",
        description="APIVersion defines the versioned schema of this representation of an object. Servers should convert recognized schemas to the latest internal value, and may reject unrecognized values. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#resources",
    )
    kind: Literal["PodCertificateRequest"] = Field(
        default="PodCertificateRequest",
        alias="kind",
        description="Kind is a string value representing the REST resource this object represents. Servers may infer this from the endpoint the client submits requests to. Cannot be updated. In CamelCase. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds",
    )
    spec: PodCertificateRequestSpec = Field(
        ...,
        alias="spec",
        description="spec contains the details about the certificate being requested.",
    )
    status: PodCertificateRequestStatus | None = Field(
        default=None,
        alias="status",
        description="status contains the issued certificate, and a standard set of conditions.",
    )
