from __future__ import annotations

from enum import Enum
from functools import cached_property
from typing import TYPE_CHECKING, Any, Generic, Literal, Self, Type

from pydantic import create_model

from kubex.models.typing import ResourceType

if TYPE_CHECKING:
    from kubex.models.list_entity import ListEntity


class Scope(Enum):
    CLUSTER = "cluster"
    NAMESPACE = "namespace"


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
    ) -> None:
        self._version = version
        self._kind = kind
        self._plural = plural
        self._scope = scope
        self._group = group
        self._list_model = list_model

    def __get__(self, instance: Any, owner: Type[ResourceType]) -> Self:
        """Fill in the missing values from the owner."""
        if kind_field := owner.model_fields.get("kind"):
            if kind_field.default is not None:
                self._kind = kind_field.default
            else:
                return self
        if self._version is None or self._group is None:
            if api_version_field := owner.model_fields.get("api_version"):
                if api_version_field.default is not None:
                    self._version, self._group = get_version_and_froup_from_api_version(
                        api_version_field.default
                    )
            else:
                return self
        if self._list_model is None:
            self._list_model = create_list_model(owner, self)
        if self._scope is None:
            self._scope = Scope.NAMESPACE
        if self._plural is None:
            if self._kind is None:
                raise ValueError("kind is not set")
            if self._kind.endswith("y"):
                self._plural = f"{self._kind[:-1].lower()}ies"
            elif self._kind.endswith("s") or self._kind.endswith("x"):
                self._plural = f"{self._kind.lower()}es"
            else:
                self._plural = f"{self._kind.lower()}s"
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


def create_list_model(
    single_model: Type[ResourceType], resource_config: ResourceConfig[ResourceType]
) -> Type[ListEntity[ResourceType]]:
    from kubex.models.list_entity import ListEntity
    from kubex.models.metadata import ListMetadata

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
