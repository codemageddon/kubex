from kubex.k8s.v1_33.storage.v1.volume_error import VolumeError
from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class VolumeAttachmentStatus(BaseK8sModel):
    """VolumeAttachmentStatus is the status of a VolumeAttachment request."""

    attach_error: VolumeError | None = Field(
        default=None,
        alias="attachError",
        description="attachError represents the last error encountered during attach operation, if any. This field must only be set by the entity completing the attach operation, i.e. the external-attacher.",
    )
    attached: bool = Field(
        ...,
        alias="attached",
        description="attached indicates the volume is successfully attached. This field must only be set by the entity completing the attach operation, i.e. the external-attacher.",
    )
    attachment_metadata: dict[str, str] | None = Field(
        default=None,
        alias="attachmentMetadata",
        description="attachmentMetadata is populated with any information returned by the attach operation, upon successful attach, that must be passed into subsequent WaitForAttach or Mount calls. This field must only be set by the entity completing the attach operation, i.e. the external-attacher.",
    )
    detach_error: VolumeError | None = Field(
        default=None,
        alias="detachError",
        description="detachError represents the last error encountered during detach operation, if any. This field must only be set by the entity completing the detach operation, i.e. the external-attacher.",
    )
