from pydantic import Field

from kubex_core.models.base import BaseK8sModel


class ServiceReference(BaseK8sModel):
    """ServiceReference holds a reference to Service.legacy.k8s.io"""

    name: str = Field(
        ..., alias="name", description="name is the name of the service. Required"
    )
    namespace: str = Field(
        ...,
        alias="namespace",
        description="namespace is the namespace of the service. Required",
    )
    path: str | None = Field(
        default=None,
        alias="path",
        description="path is an optional URL path at which the webhook will be contacted.",
    )
    port: int | None = Field(
        default=None,
        alias="port",
        description="port is an optional service port at which the webhook will be contacted. `port` should be a valid port number (1-65535, inclusive). Defaults to 443 for backward compatibility.",
    )
