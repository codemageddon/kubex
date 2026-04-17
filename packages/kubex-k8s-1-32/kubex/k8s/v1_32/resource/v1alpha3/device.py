from kubex.k8s.v1_32.resource.v1alpha3.basic_device import BasicDevice
from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class Device(BaseK8sModel):
    """Device represents one individual hardware instance that can be selected based on its attributes. Besides the name, exactly one field must be set."""

    basic: BasicDevice | None = Field(
        default=None, alias="basic", description="Basic defines one device instance."
    )
    name: str = Field(
        ...,
        alias="name",
        description="Name is unique identifier among all devices managed by the driver in the pool. It must be a DNS label.",
    )
