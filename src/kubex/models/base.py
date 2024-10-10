import datetime
from enum import Enum
from typing import ClassVar, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class HasStatusSubresource: ...


class HasReplicasSubresource: ...


class PodProtocol: ...


class BaseK8sModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel)


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

    name: str


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


class ResourceConfig(BaseK8sModel):
    """ResourceConfig is the configuration for a resource."""

    version: str
    kind: str
    plural: str
    scope: Scope
    group: str | None = None

    """/apis/{group}/{version}/{url_path_segment} for non-core resources
    /api/{version}/{url_path_segment} for core resources
    """

    def url(self, namespace: str | None = None) -> str:
        """url returns the URL for the resource."""
        if self.group and self.group != "core":
            api_version = f"/apis/{self.group}/{self.version}"
        else:
            api_version = f"/api/{self.version}"

        if namespace is None:
            return f"{api_version}/{self.plural}"
        elif self.scope == Scope.CLUSTER:
            raise ValueError("resource is cluster-scoped")
        return f"{api_version}/namespaces/{namespace}/{self.plural}"


class BaseEntity(BaseK8sModel):
    """BaseEntity is the common fields for all entities."""

    __RESOURCE_CONFIG__: ClassVar[ResourceConfig]

    api_version: str
    kind: str
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
