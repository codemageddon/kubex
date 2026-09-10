import datetime

from pydantic import Field

from kubex_core.models.base import BaseK8sModel


class StorageHealthCondition(BaseK8sModel):
    """StorageHealthCondition represents an adverse health condition reported by a CSI driver for its storage backend on a node."""

    access_mode: str | None = Field(
        default=None,
        alias="accessMode",
        description="accessMode is the access mode affected. Nil means all access modes are affected.",
    )
    last_transition_time: datetime.datetime | None = Field(
        default=None,
        alias="lastTransitionTime",
        description="lastTransitionTime is when this condition first appeared at its current state.",
    )
    message: str | None = Field(
        default=None,
        alias="message",
        description="message is a human-readable description. Maximum permitted length of a message is 1024 characters.",
    )
    reason: str = Field(
        ...,
        alias="reason",
        description="reason is a brief CamelCase machine-parseable reason. Maximum permitted length of a reason is 256 characters.",
    )
    status: str = Field(
        ...,
        alias="status",
        description='status is the health status category. One of "StorageUnreachable", "StorageDegraded".',
    )
    volume_mode: str | None = Field(
        default=None,
        alias="volumeMode",
        description="volumeMode is the volume mode affected. Nil means both are affected.",
    )
