from __future__ import annotations

import datetime
from enum import Enum
from functools import cached_property
from typing import Any, ClassVar, Generic, Literal, Self, Type, TypeVar

from pydantic import BaseModel, ConfigDict, Field, create_model
from pydantic.alias_generators import to_camel


class BaseK8sModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class Scope(Enum):
    CLUSTER = "cluster"
    NAMESPACE = "namespace"


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


class OwnerReference(BaseK8sModel):
    """OwnerReference contains enough information to let you identify an owning object."""

    api_version: str
    kind: str
    name: str
    uid: str
    controller: bool | None = None
    block_owner_deletion: bool | None = None


# class ClusterScopedMetadata(ObjectMetadata):
#     """ClusterScopedMetadata is the common metadata for all Kubernetes API objects that are cluster-scoped."""

#     name: str | None = None
#     generate_name: str | None = None


# class NamespaceScopedMetadata(ObjectMetadata):
#     """NamespaceScopedMetadata is the common metadata for all Kubernetes API objects that are namespace-scoped."""

#     name: str | None = None
#     namespace: str | None = None
#     generate_name: str | None = None
#     owner_references: list[OwnerReference] | None = None


class ListMetadata(BaseK8sModel):
    """ListMeta describes metadata that synthetic resources must have, including lists and various status objects."""

    continue_: str | None = Field(None, alias="continue")
    remaining_item_count: int | None = None
    resource_version: str | None = None
    self_link: str | None = None


class BaseEntity(BaseK8sModel):
    """BaseEntity is the common fields for all entities."""

    __RESOURCE_CONFIG__: ClassVar[ResourceConfig[Self]]

    api_version: str | None = None
    kind: str | None = None
    metadata: ObjectMetadata


ResourceType = TypeVar("ResourceType", bound=BaseEntity)


class PartialObjectMetadataList(BaseK8sModel):
    api_version: Literal["meta.k8s.io/v1"] = "meta.k8s.io/v1"
    kind: Literal["PartialObjectMetadataList"] = "PartialObjectMetadataList"
    metadata: ListMetadata
    items: list[ObjectMetadata]


class ListEntity(BaseK8sModel, Generic[ResourceType]):
    """ListEntity is the common fields for all list entities."""

    api_version: str
    kind: str
    metadata: ListMetadata
    items: list[ResourceType]


class ResourceConfig(Generic[ResourceType]):
    """ResourceConfig is the configuration for a resource."""

    def __init__(
        self,
        version: str | None = None,
        kind: str | None = None,
        plural: str | None = None,
        scope: Scope | None = None,
        group: str | None = None,
        list_model: Type[ListEntity[ResourceType]] | None = None,
        partial_metadata_model: Type[PartialObjectMetadata[ObjectMetadata]]
        | None = None,
        partial_metadata_list_model: Type[PartialObjectMetadataList[ObjectMetadata]]
        | None = None,
    ) -> None:
        self._version = version
        self._kind = kind
        self._plural = plural
        self._scope = scope
        self._group = group
        self._list_model = list_model

    def __get__(self, instance: Any, owner: Type[ResourceType]) -> Self:
        """Fill in the missing values from the owner."""
        if self._list_model is None:
            self._list_model = create_list_model(owner, self)
        if self._version is None or self._group is None:
            self._version, self._group = get_version_and_froup_from_api_version(
                owner.api_version
            )
        if self._kind is None:
            self._kind = owner.kind
        if self._scope is None:
            if issubclass(owner, ClusterScopedEntity):
                self._scope = Scope.CLUSTER
            else:
                self._scope = Scope.NAMESPACE
        if self._plural is None:
            if owner.kind is None:
                raise ValueError("kind is not set")
            if owner.kind.endswith("y"):
                self._plural = f"{owner.kind[:-1].lower()}ies"
            elif owner.kind.endswith("s") or owner.kind.endswith("x"):
                self._plural = f"{owner.kind.lower()}es"
            else:
                self._plural = f"{owner.kind.lower()}s"
        return self

    @property
    def version(self) -> str:
        if self._version is None:
            raise ValueError("version is not set")
        return self._version

    @property
    def kind(self) -> str:
        if self._kind is None:
            raise ValueError("kind is not set")
        return self._kind

    @property
    def plural(self) -> str:
        if self._plural is None:
            raise ValueError("plural is not set")
        return self._plural

    @property
    def scope(self) -> Scope:
        if self._scope is None:
            raise ValueError("scope is not set")
        return self._scope

    @property
    def group(self) -> str:
        if self._group is None:
            raise ValueError("group is not set")
        return self._group

    @property
    def list_model(self) -> Type[ListEntity[ResourceType]]:
        if self._list_model is None:
            raise ValueError("list_model is not set")
        return self._list_model

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
            raise ValueError("resource is cluster-scoped but namespace is set")
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


class PartialObjectMetadata(BaseEntity):
    """PartialObjectMetadata is the common metadata for all Kubernetes API objects."""

    __RESOURCE_CONFIG__: ClassVar[ResourceConfig[PartialObjectMetadata]] = (
        ResourceConfig["PartialObjectMetadata"](
            version="v1",
            kind="PartialObjectMetadata",
            group="meta.k8s.io",
            plural="",
            scope=Scope.CLUSTER,
        )
    )

    api_version: Literal["meta.k8s.io/v1"] = "meta.k8s.io/v1"
    kind: Literal["PartialObjectMetadata"] = "PartialObjectMetadata"
    metadata: ObjectMetadata


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


def get_version_and_froup_from_api_version(api_version: str | None) -> tuple[str, str]:
    """get_version_and_group_from_api_version returns the version and group from the apiVersion."""
    if api_version is None:
        raise ValueError("api_version is not set")
    parts = api_version.split("/")
    if len(parts) == 1:
        return parts[0], "core"
    return parts[1], parts[0]


class ClusterScopedEntity(BaseEntity): ...


class NamespaceScopedEntity(BaseEntity): ...


class HasStatusSubresource(BaseEntity): ...


class HasScaleSubresource(BaseEntity): ...


class HasLogs(BaseEntity): ...


class Evictable(BaseEntity): ...
