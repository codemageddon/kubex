from pydantic import Field

from kubex.k8s.v1_34.storage.v1.volume_attachment_source import VolumeAttachmentSource
from kubex_core.models.base import BaseK8sModel


class VolumeAttachmentSpec(BaseK8sModel):
    """VolumeAttachmentSpec is the specification of a VolumeAttachment request."""

    attacher: str = Field(
        ...,
        alias="attacher",
        description="attacher indicates the name of the volume driver that MUST handle this request. This is the name returned by GetPluginName().",
    )
    node_name: str = Field(
        ...,
        alias="nodeName",
        description="nodeName represents the node that the volume should be attached to.",
    )
    source: VolumeAttachmentSource = Field(
        ...,
        alias="source",
        description="source represents the volume that should be attached.",
    )
