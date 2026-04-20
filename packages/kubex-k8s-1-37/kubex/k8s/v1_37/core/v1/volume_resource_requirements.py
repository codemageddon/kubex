from pydantic import Field

from kubex_core.models.base import BaseK8sModel


class VolumeResourceRequirements(BaseK8sModel):
    """VolumeResourceRequirements describes the storage resource requirements for a volume."""

    limits: dict[str, str] | None = Field(
        default=None,
        alias="limits",
        description="Limits describes the maximum amount of compute resources allowed. More info: https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/",
    )
    requests: dict[str, str] | None = Field(
        default=None,
        alias="requests",
        description="Requests describes the minimum amount of compute resources required. If Requests is omitted for a container, it defaults to Limits if that is explicitly specified, otherwise to an implementation-defined value. Requests cannot exceed Limits. More info: https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/",
    )
