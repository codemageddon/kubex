from __future__ import annotations

from typing import Literal

from kubex_core.models.base_entity import BaseEntity
from kubex_core.models.metadata import ObjectMetadata


class PartialObjectMetadata(BaseEntity):
    """PartialObjectMetadata is the common metadata for all Kubernetes API objects."""

    api_version: Literal["meta.k8s.io/v1"] = "meta.k8s.io/v1"
    kind: Literal["PartialObjectMetadata"] = "PartialObjectMetadata"
    metadata: ObjectMetadata
