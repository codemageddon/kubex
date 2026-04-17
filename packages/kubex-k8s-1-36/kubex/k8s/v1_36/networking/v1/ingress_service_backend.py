from kubex.k8s.v1_36.networking.v1.service_backend_port import ServiceBackendPort
from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class IngressServiceBackend(BaseK8sModel):
    """IngressServiceBackend references a Kubernetes Service as a Backend."""

    name: str = Field(
        ...,
        alias="name",
        description="name is the referenced service. The service must exist in the same namespace as the Ingress object.",
    )
    port: ServiceBackendPort | None = Field(
        default=None,
        alias="port",
        description="port of the referenced service. A port name or port number is required for a IngressServiceBackend.",
    )
