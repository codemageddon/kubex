from kubex.k8s.v1_35.core.v1.object_field_selector import ObjectFieldSelector
from kubex.k8s.v1_35.core.v1.resource_field_selector import ResourceFieldSelector
from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class DownwardAPIVolumeFile(BaseK8sModel):
    """DownwardAPIVolumeFile represents information to create the file containing the pod field"""

    field_ref: ObjectFieldSelector | None = Field(
        default=None,
        alias="fieldRef",
        description="Required: Selects a field of the pod: only annotations, labels, name, namespace and uid are supported.",
    )
    mode: int | None = Field(
        default=None,
        alias="mode",
        description="Optional: mode bits used to set permissions on this file, must be an octal value between 0000 and 0777 or a decimal value between 0 and 511. YAML accepts both octal and decimal values, JSON requires decimal values for mode bits. If not specified, the volume defaultMode will be used. This might be in conflict with other options that affect the file mode, like fsGroup, and the result can be other mode bits set.",
    )
    path: str = Field(
        ...,
        alias="path",
        description="Required: Path is the relative path name of the file to be created. Must not be absolute or contain the '..' path. Must be utf-8 encoded. The first item of the relative path must not start with '..'",
    )
    resource_field_ref: ResourceFieldSelector | None = Field(
        default=None,
        alias="resourceFieldRef",
        description="Selects a resource of the container: only resources limits and requests (limits.cpu, limits.memory, requests.cpu and requests.memory) are currently supported.",
    )
