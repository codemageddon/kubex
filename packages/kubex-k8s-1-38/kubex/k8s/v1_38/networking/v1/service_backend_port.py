from pydantic import Field

from kubex_core.models.base import BaseK8sModel


class ServiceBackendPort(BaseK8sModel):
    """ServiceBackendPort is the service port being referenced."""

    name: str | None = Field(
        default=None,
        alias="name",
        description='name is the name of the port on the Service. This is a mutually exclusive setting with "Number".',
    )
    number: int | None = Field(
        default=None,
        alias="number",
        description='number is the numerical port number (e.g. 80) on the Service. This is a mutually exclusive setting with "Name".',
    )
