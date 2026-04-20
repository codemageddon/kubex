from pydantic import Field

from kubex_core.models.base import BaseK8sModel


class DeviceAttribute(BaseK8sModel):
    """DeviceAttribute must have exactly one field set."""

    bool_: bool | None = Field(
        default=None, alias="bool", description="BoolValue is a true/false value."
    )
    int_: int | None = Field(
        default=None, alias="int", description="IntValue is a number."
    )
    string: str | None = Field(
        default=None,
        alias="string",
        description="StringValue is a string. Must not be longer than 64 characters.",
    )
    version: str | None = Field(
        default=None,
        alias="version",
        description="VersionValue is a semantic version according to semver.org spec 2.0.0. Must not be longer than 64 characters.",
    )
