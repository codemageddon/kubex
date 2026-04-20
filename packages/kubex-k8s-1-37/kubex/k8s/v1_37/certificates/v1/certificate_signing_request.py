from __future__ import annotations

from typing import ClassVar, Literal

from pydantic import Field

from kubex.k8s.v1_37.certificates.v1.certificate_signing_request_spec import (
    CertificateSigningRequestSpec,
)
from kubex.k8s.v1_37.certificates.v1.certificate_signing_request_status import (
    CertificateSigningRequestStatus,
)
from kubex_core.models.interfaces import ClusterScopedEntity, HasStatusSubresource
from kubex_core.models.resource_config import ResourceConfig, Scope


class CertificateSigningRequest(ClusterScopedEntity, HasStatusSubresource):
    """CertificateSigningRequest objects provide a mechanism to obtain x509 certificates by submitting a certificate signing request, and having it asynchronously approved and issued. Kubelets use this API to obtain: 1. client certificates to authenticate to kube-apiserver (with the "kubernetes.io/kube-apiserver-client-kubelet" signerName). 2. serving certificates for TLS endpoints kube-apiserver can connect to securely (with the "kubernetes.io/kubelet-serving" signerName). This API can be used to request client certificates to authenticate to kube-apiserver (with the "kubernetes.io/kube-apiserver-client" signerName), or to obtain certificates from custom non-Kubernetes signers."""

    __RESOURCE_CONFIG__: ClassVar[ResourceConfig["CertificateSigningRequest"]] = (
        ResourceConfig["CertificateSigningRequest"](
            version="v1",
            kind="CertificateSigningRequest",
            group="certificates.k8s.io",
            plural="certificatesigningrequests",
            scope=Scope.CLUSTER,
        )
    )
    api_version: Literal["certificates.k8s.io/v1"] = Field(
        default="certificates.k8s.io/v1",
        alias="apiVersion",
        description="APIVersion defines the versioned schema of this representation of an object. Servers should convert recognized schemas to the latest internal value, and may reject unrecognized values. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#resources",
    )
    kind: Literal["CertificateSigningRequest"] = Field(
        default="CertificateSigningRequest",
        alias="kind",
        description="Kind is a string value representing the REST resource this object represents. Servers may infer this from the endpoint the client submits requests to. Cannot be updated. In CamelCase. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds",
    )
    spec: CertificateSigningRequestSpec = Field(
        ...,
        alias="spec",
        description="spec contains the certificate request, and is immutable after creation. Only the request, signerName, expirationSeconds, and usages fields can be set on creation. Other fields are derived by Kubernetes and cannot be modified by users.",
    )
    status: CertificateSigningRequestStatus | None = Field(
        default=None,
        alias="status",
        description="status contains information about whether the request is approved or denied, and the certificate issued by the signer, or the failure condition indicating signer failure.",
    )
