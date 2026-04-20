import datetime

from pydantic import Field

from kubex_core.models.base import BaseK8sModel


class VolumeError(BaseK8sModel):
    """VolumeError captures an error encountered during a volume operation."""

    error_code: int | None = Field(
        default=None,
        alias="errorCode",
        description="errorCode is a numeric gRPC code representing the error encountered during Attach or Detach operations. This is an optional, beta field that requires the MutableCSINodeAllocatableCount feature gate being enabled to be set.",
    )
    message: str | None = Field(
        default=None,
        alias="message",
        description="message represents the error encountered during Attach or Detach operation. This string may be logged, so it should not contain sensitive information.",
    )
    time: datetime.datetime | None = Field(
        default=None,
        alias="time",
        description="time represents the time the error was encountered.",
    )
