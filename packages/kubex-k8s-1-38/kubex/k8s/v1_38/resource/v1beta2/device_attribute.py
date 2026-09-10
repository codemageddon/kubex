from pydantic import Field

from kubex_core.models.base import BaseK8sModel


class DeviceAttribute(BaseK8sModel):
    """DeviceAttribute must have exactly one field set."""

    bool_: bool | None = Field(
        default=None, alias="bool", description="BoolValue is a true/false value."
    )
    bools: list[bool] | None = Field(
        default=None,
        alias="bools",
        description="BoolValues is a non-empty list of true/false values.",
    )
    int_: int | None = Field(
        default=None, alias="int", description="IntValue is a number."
    )
    ints: list[int] | None = Field(
        default=None,
        alias="ints",
        description="IntValues is a non-empty list of numbers. This is an alpha field and requires enabling the DRAListTypeAttributes feature gate.",
    )
    string: str | None = Field(
        default=None,
        alias="string",
        description="StringValue is a string. Must not be longer than 64 characters.",
    )
    strings: list[str] | None = Field(
        default=None,
        alias="strings",
        description="StringValues is a non-empty list of strings. Each string must not be longer than 64 characters. This is an alpha field and requires enabling the DRAListTypeAttributes feature gate.",
    )
    version: str | None = Field(
        default=None,
        alias="version",
        description="VersionValue is a semantic version according to semver.org spec 2.0.0. Must not be longer than 64 characters.",
    )
    versions: list[str] | None = Field(
        default=None,
        alias="versions",
        description="VersionValues is a non-empty list of semantic versions according to semver.org spec 2.0.0. Each version string must not be longer than 64 characters. This is an alpha field and requires enabling the DRAListTypeAttributes feature gate.",
    )
