from pydantic import Field

from kubex_core.models.base import BaseK8sModel


class QuobyteVolumeSource(BaseK8sModel):
    """Represents a Quobyte mount that lasts the lifetime of a pod. Quobyte volumes do not support ownership management or SELinux relabeling."""

    group: str | None = Field(
        default=None,
        alias="group",
        description="group to map volume access to Default is no group",
    )
    read_only: bool | None = Field(
        default=None,
        alias="readOnly",
        description="readOnly here will force the Quobyte volume to be mounted with read-only permissions. Defaults to false.",
    )
    registry: str = Field(
        ...,
        alias="registry",
        description="registry represents a single or multiple Quobyte Registry services specified as a string as host:port pair (multiple entries are separated with commas) which acts as the central registry for volumes",
    )
    tenant: str | None = Field(
        default=None,
        alias="tenant",
        description="tenant owning the given Quobyte volume in the Backend Used with dynamically provisioned Quobyte volumes, value is set by the plugin",
    )
    user: str | None = Field(
        default=None,
        alias="user",
        description="user to map volume access to Defaults to serivceaccount user",
    )
    volume: str = Field(
        ...,
        alias="volume",
        description="volume is a string that references an already created Quobyte volume by name.",
    )
