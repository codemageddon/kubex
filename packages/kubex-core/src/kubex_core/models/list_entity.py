from typing import Generic

from kubex_core.models.base import BaseK8sModel
from kubex_core.models.metadata import ListMetadata
from kubex_core.models.typing import ResourceType


class ListEntity(BaseK8sModel, Generic[ResourceType]):
    """ListEntity is the common fields for all list entities."""

    api_version: str
    kind: str
    metadata: ListMetadata
    items: list[ResourceType]
