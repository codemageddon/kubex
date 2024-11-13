from typing import ClassVar, Self

from kubex.models.base import BaseK8sModel
from kubex.models.metadata import ObjectMetadata
from kubex.models.resource_config import ResourceConfig


class BaseEntity(BaseK8sModel):
    """BaseEntity is the common fields for all entities."""

    __RESOURCE_CONFIG__: ClassVar[ResourceConfig[Self]] = ResourceConfig()

    api_version: str | None = None
    kind: str | None = None
    metadata: ObjectMetadata
