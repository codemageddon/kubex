from __future__ import annotations

from typing import Any

from pydantic import Field

from kubex_core.models.base import BaseK8sModel
from kubex_core.models.types import Time


class OwnerReference(BaseK8sModel):
    """OwnerReference contains enough information to let you identify an owning object."""

    api_version: str
    kind: str
    name: str
    uid: str
    controller: bool | None = None
    block_owner_deletion: bool | None = None


class ManagedFieldsEntry(BaseK8sModel):
    """ManagedFieldsEntry is a workflow-id, a FieldSet and the group version of the resource that the fieldset applies to."""

    api_version: str | None = None
    fields_type: str | None = None
    fields_v1: dict[str, Any] | None = Field(None, alias="fieldsV1")
    manager: str | None = None
    operation: str | None = None
    subresource: str | None = None
    time: Time | None = None


class ObjectMetadata(BaseK8sModel):
    """CommonMetadata is the common metadata for all Kubernetes API objects."""

    labels: dict[str, str] | None = None
    annotations: dict[str, str] | None = None
    finalizers: list[str] | None = None
    creation_timestamp: Time | None = None
    deletion_timestamp: Time | None = None
    deletion_grace_period_seconds: int | None = None
    generation: int | None = None
    resource_version: str | None = None
    uid: str | None = None
    name: str | None = None
    namespace: str | None = None
    generate_name: str | None = None
    owner_references: list[OwnerReference] | None = None
    managed_fields: list[ManagedFieldsEntry] | None = None
    self_link: str | None = None
    """Deprecated: no longer populated by the API server."""


class ShardInfo(BaseK8sModel):
    """ShardInfo describes the shard selector that was applied to produce a list response."""

    selector: str


class ListMetadata(BaseK8sModel):
    """ListMeta describes metadata that synthetic resources must have, including lists and various status objects."""

    continue_: str | None = Field(None, alias="continue")
    remaining_item_count: int | None = None
    resource_version: str | None = None
    self_link: str | None = None
    shard_info: ShardInfo | None = None
    """Set on sharded list responses (alpha, Kubernetes 1.36+)."""
