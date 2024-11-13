from typing import Generic

from kubex.models.base import BaseK8sModel
from kubex.models.metadata import ListMetadata
from kubex.models.typing import ResourceType


class ListEntity(BaseK8sModel, Generic[ResourceType]):
    """ListEntity is the common fields for all list entities."""

    api_version: str
    kind: str
    metadata: ListMetadata
    items: list[ResourceType]
