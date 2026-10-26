from pydantic import Field

from kubex_core.models.base import BaseK8sModel
from kubex_core.models.types import Time


class VolumeError(BaseK8sModel):
    """VolumeError captures an error encountered during a volume operation."""

    message: str | None = Field(
        default=None,
        alias="message",
        description="message represents the error encountered during Attach or Detach operation. This string may be logged, so it should not contain sensitive information.",
    )
    time: Time | None = Field(
        default=None,
        alias="time",
        description="time represents the time the error was encountered.",
    )
