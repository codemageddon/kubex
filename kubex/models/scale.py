from typing import Literal

from .base import BaseEntity, BaseK8sModel, ObjectMetadata


class ScaleSpec(BaseK8sModel):
    replicas: int


class ScaleStatus(BaseK8sModel):
    replicas: int
    selector: str | None = None


class Scale(BaseEntity):
    api_version: Literal["autoscaling/v1"] = "autoscaling/v1"
    kind: Literal["Scale"] = "Scale"
    metadata: ObjectMetadata
    spec: ScaleSpec
    status: dict[str, int] | None = None
