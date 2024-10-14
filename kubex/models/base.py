from __future__ import annotations
import datetime
from enum import Enum
from typing import ClassVar, Generic, TypeVar, Type, Self, Literal
from functools import cached_property

from pydantic import BaseModel, ConfigDict, Field, create_model
from pydantic.alias_generators import to_camel
from dataclasses import dataclass


class HasStatusSubresource: ...


class HasReplicasSubresource: ...


class PodProtocol: ...


class BaseK8sModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class Scope(Enum):
    CLUSTER = "cluster"
    NAMESPACE = "namespace"


class CommonMetadata(BaseK8sModel):
    """CommonMetadata is the common metadata for all Kubernetes API objects."""

    labels: dict[str, str] | None = None
    annotations: dict[str, str] | None = None
    finalizers: list[str] | None = None
    creation_timestamp: datetime.datetime | None = None
    deletion_timestamp: datetime.datetime | None = None
    deletion_grace_period_seconds: int | None = None
    resource_version: str | None = None
    uid: str | None = None


class OwnerReference(BaseK8sModel):
    """OwnerReference contains enough information to let you identify an owning object."""

    api_version: str
    kind: str
    name: str
    uid: str
    controller: bool | None = None
    block_owner_deletion: bool | None = None


class ClusterScopedMetadata(CommonMetadata):
    """ClusterScopedMetadata is the common metadata for all Kubernetes API objects that are cluster-scoped."""

    name: str | None = None
    generate_name: str | None = None


class NamespaceScopedMetadata(CommonMetadata):
    """NamespaceScopedMetadata is the common metadata for all Kubernetes API objects that are namespace-scoped."""

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


class BaseEntity(BaseK8sModel):
    """BaseEntity is the common fields for all entities."""

    __RESOURCE_CONFIG__: ClassVar[ResourceConfig[Self]]  # type: ignore[type-var]

    api_version: str | None = None
    kind: str | None = None
    metadata: CommonMetadata


class ClusterScopedEntity(BaseEntity):
    """ClusterScopedEntity is the common fields for all cluster-scoped entities."""

    metadata: ClusterScopedMetadata


class NamespaceScopedEntity(BaseEntity):
    """NamespaceScopedEntity is the common fields for all namespace-scoped entities."""

    metadata: NamespaceScopedMetadata


ResourceType = TypeVar(
    "ResourceType", bound=ClusterScopedEntity | NamespaceScopedEntity
)


class ListEntity(BaseK8sModel, Generic[ResourceType]):
    """ListEntity is the common fields for all list entities."""

    api_version: str
    kind: str
    metadata: ListMetadata
    items: list[ResourceType]


@dataclass
class ResourceConfig(Generic[ResourceType]):
    """ResourceConfig is the configuration for a resource."""

    version: str
    kind: str
    plural: str
    scope: Scope
    group: str | None = None
    list_model: Type[ListEntity[ResourceType]] | None = None

    def __get__(self, instance: Self | None, owner: Type[ResourceType]) -> Self:
        if self.list_model is None:
            self.list_model = create_list_model(owner, self)
        return self

    def url(self, namespace: str | None = None, name: str | None = None) -> str:
        """url returns the URL for the resource."""
        if self.group and self.group != "core":
            api_version = f"/apis/{self.group}/{self.version}"
        else:
            api_version = f"/api/{self.version}"

        url: str
        if namespace is None:
            url = f"{api_version}/{self.plural}"
        elif self.scope == Scope.CLUSTER:
            raise ValueError("resource is cluster-scoped")
        else:
            url = f"{api_version}/namespaces/{namespace}/{self.plural}"

        if name is None:
            return url
        return f"{url}/{name}"

    @cached_property
    def api_version(self) -> str:
        if self.group and self.group != "core":
            return f"{self.group}/{self.version}"
        return self.version


def create_list_model(
    single_model: Type[ResourceType], resource_config: ResourceConfig[ResourceType]
) -> Type[ListEntity[ResourceType]]:
    kind = f"{resource_config.kind}List"
    list_model = create_model(
        kind,
        api_version=(Literal[resource_config.api_version], resource_config.api_version),
        kind=(Literal[kind], kind),
        metadata=(ListMetadata, ...),
        items=(list[single_model], ...),  # type: ignore[valid-type]
        __base__=ListEntity[single_model],  # type: ignore[valid-type]
    )
    return list_model
