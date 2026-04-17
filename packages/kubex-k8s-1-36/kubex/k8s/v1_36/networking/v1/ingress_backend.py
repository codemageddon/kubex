from kubex.k8s.v1_36.core.v1.typed_local_object_reference import (
    TypedLocalObjectReference,
)
from kubex.k8s.v1_36.networking.v1.ingress_service_backend import IngressServiceBackend
from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class IngressBackend(BaseK8sModel):
    """IngressBackend describes all endpoints for a given service and port."""

    resource: TypedLocalObjectReference | None = Field(
        default=None,
        alias="resource",
        description='resource is an ObjectRef to another Kubernetes resource in the namespace of the Ingress object. If resource is specified, a service.Name and service.Port must not be specified. This is a mutually exclusive setting with "Service".',
    )
    service: IngressServiceBackend | None = Field(
        default=None,
        alias="service",
        description='service references a service as a backend. This is a mutually exclusive setting with "Resource".',
    )
