from pydantic import Field

from kubex_core.models.base import BaseK8sModel


class ServiceReference(BaseK8sModel):
    """ServiceReference holds a reference to Service.legacy.k8s.io"""

    name: str | None = Field(
        default=None, alias="name", description="Name is the name of the service"
    )
    namespace: str | None = Field(
        default=None,
        alias="namespace",
        description="Namespace is the namespace of the service",
    )
    port: int | None = Field(
        default=None,
        alias="port",
        description="If specified, the port on the service that hosting webhook. Default to 443 for backward compatibility. `port` should be a valid port number (1-65535, inclusive).",
    )
