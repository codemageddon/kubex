from __future__ import annotations

import datetime

from pydantic import Field

from kubex.models.base import BaseK8sModel


class OwnerReference(BaseK8sModel):
    """OwnerReference contains enough information to let you identify an owning object."""

    api_version: str
    kind: str
    name: str
    uid: str
    controller: bool | None = None
    block_owner_deletion: bool | None = None


class ObjectMetadata(BaseK8sModel):
    """CommonMetadata is the common metadata for all Kubernetes API objects."""

    labels: dict[str, str] | None = None
    annotations: dict[str, str] | None = None
    finalizers: list[str] | None = None
    creation_timestamp: datetime.datetime | None = None
    deletion_timestamp: datetime.datetime | None = None
    deletion_grace_period_seconds: int | None = None
    generation: int | None = None
    resource_version: str | None = None
    uid: str | None = None
    name: str | None = None
    namespace: str | None = None
    generate_name: str | None = None
    owner_references: list[OwnerReference] | None = None


class ListMetadata(BaseK8sModel):
    """ListMeta describes metadata that synthetic resources must have, including lists and various status objects."""

    continue_: str | None = Field(None, alias="continue")
    remaining_item_count: int | None = None
    resource_version: str | None = None
    self_link: str | None = None
