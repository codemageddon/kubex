from kubex.k8s.v1_34.core.v1.pod_spec import PodSpec
from kubex_core.models.base import BaseK8sModel
from kubex_core.models.metadata import ObjectMetadata
from pydantic import Field


class PodTemplateSpec(BaseK8sModel):
    """PodTemplateSpec describes the data a pod should have when created from a template"""

    metadata: ObjectMetadata | None = Field(
        default=None,
        alias="metadata",
        description="Standard object's metadata. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#metadata",
    )
    spec: PodSpec | None = Field(
        default=None,
        alias="spec",
        description="Specification of the desired behavior of the pod. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#spec-and-status",
    )
