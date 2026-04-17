from __future__ import annotations

from typing import ClassVar, Literal

from kubex.k8s.v1_32.storage.v1.volume_attachment_spec import VolumeAttachmentSpec
from kubex.k8s.v1_32.storage.v1.volume_attachment_status import VolumeAttachmentStatus
from kubex_core.models.interfaces import ClusterScopedEntity, HasStatusSubresource
from kubex_core.models.resource_config import ResourceConfig, Scope
from pydantic import Field


class VolumeAttachment(ClusterScopedEntity, HasStatusSubresource):
    """VolumeAttachment captures the intent to attach or detach the specified volume to/from the specified node. VolumeAttachment objects are non-namespaced."""

    __RESOURCE_CONFIG__: ClassVar[ResourceConfig["VolumeAttachment"]] = ResourceConfig[
        "VolumeAttachment"
    ](
        version="v1",
        kind="VolumeAttachment",
        group="storage.k8s.io",
        plural="volumeattachments",
        scope=Scope.CLUSTER,
    )
    api_version: Literal["storage.k8s.io/v1"] = Field(
        default="storage.k8s.io/v1",
        alias="apiVersion",
        description="APIVersion defines the versioned schema of this representation of an object. Servers should convert recognized schemas to the latest internal value, and may reject unrecognized values. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#resources",
    )
    kind: Literal["VolumeAttachment"] = Field(
        default="VolumeAttachment",
        alias="kind",
        description="Kind is a string value representing the REST resource this object represents. Servers may infer this from the endpoint the client submits requests to. Cannot be updated. In CamelCase. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds",
    )
    spec: VolumeAttachmentSpec = Field(
        ...,
        alias="spec",
        description="spec represents specification of the desired attach/detach volume behavior. Populated by the Kubernetes system.",
    )
    status: VolumeAttachmentStatus | None = Field(
        default=None,
        alias="status",
        description="status represents status of the VolumeAttachment request. Populated by the entity completing the attach or detach operation, i.e. the external-attacher.",
    )
