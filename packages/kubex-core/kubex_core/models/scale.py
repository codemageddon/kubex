from typing import Literal

from pydantic import Field

from .base import BaseK8sModel
from .base_entity import BaseEntity
from .metadata import ObjectMetadata


class ScaleSpec(BaseK8sModel):
    # omitempty on the wire: a scale of 0 arrives as `spec: {}`.
    replicas: int = 0


class ScaleStatus(BaseK8sModel):
    replicas: int = 0
    selector: str | None = None


class Scale(BaseEntity):
    api_version: Literal["autoscaling/v1"] = "autoscaling/v1"
    kind: Literal["Scale"] = "Scale"
    metadata: ObjectMetadata
    spec: ScaleSpec = Field(default_factory=ScaleSpec)
    status: ScaleStatus | None = None
