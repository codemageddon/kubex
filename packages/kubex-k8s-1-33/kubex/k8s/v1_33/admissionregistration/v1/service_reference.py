from pydantic import Field

from kubex_core.models.base import BaseK8sModel


class ServiceReference(BaseK8sModel):
    """ServiceReference holds a reference to Service.legacy.k8s.io"""

    name: str = Field(
        ..., alias="name", description="`name` is the name of the service. Required"
    )
    namespace: str = Field(
        ...,
        alias="namespace",
        description="`namespace` is the namespace of the service. Required",
    )
    path: str | None = Field(
        default=None,
        alias="path",
        description="`path` is an optional URL path which will be sent in any request to this service.",
    )
    port: int | None = Field(
        default=None,
        alias="port",
        description="If specified, the port on the service that hosting webhook. Default to 443 for backward compatibility. `port` should be a valid port number (1-65535, inclusive).",
    )
