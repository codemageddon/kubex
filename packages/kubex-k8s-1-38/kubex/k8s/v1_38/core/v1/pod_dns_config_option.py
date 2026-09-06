from pydantic import Field

from kubex_core.models.base import BaseK8sModel


class PodDNSConfigOption(BaseK8sModel):
    """PodDNSConfigOption defines DNS resolver options of a pod."""

    name: str | None = Field(
        default=None,
        alias="name",
        description="Name is this DNS resolver option's name. Required.",
    )
    value: str | None = Field(
        default=None,
        alias="value",
        description="Value is this DNS resolver option's value.",
    )
