from __future__ import annotations

from typing import ClassVar, Literal

from kubex_core.models.base_entity import BaseEntity
from kubex_core.models.metadata import ObjectMetadata
from kubex_core.models.resource_config import ResourceConfig, Scope


class PartialObjectMetadata(BaseEntity):
    """PartialObjectMetadata is the common metadata for all Kubernetes API objects."""

    __RESOURCE_CONFIG__: ClassVar[ResourceConfig["PartialObjectMetadata"]] = (
        ResourceConfig["PartialObjectMetadata"](
            version="v1",
            kind="PartialObjectMetadata",
            group="meta.k8s.io",
            plural="partialobjectmetadatas",
            scope=Scope.NAMESPACE,
        )
    )

    api_version: Literal["meta.k8s.io/v1"] = "meta.k8s.io/v1"
    kind: Literal["PartialObjectMetadata"] = "PartialObjectMetadata"
    metadata: ObjectMetadata
