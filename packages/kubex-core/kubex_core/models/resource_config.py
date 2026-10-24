from __future__ import annotations

from enum import Enum
from functools import cached_property
from typing import TYPE_CHECKING, Any, Generic, Literal, Self, Type, cast

from pydantic import create_model

from kubex_core.models.typing import ResourceType

if TYPE_CHECKING:
    from kubex_core.models.list_entity import ListEntity


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
        """Return the resource config for `owner`, filling in missing values from it.

        `owner` is not necessarily the class that declared this descriptor: a
        `BaseEntity` subclass that omits its own `__RESOURCE_CONFIG__` inherits
        this one from `BaseEntity` and shares it with every other such
        subclass. Filling it in used to mutate that shared instance in place,
        so whichever subclass resolved it first silently won for all the
        others. Instead, a private copy is cached on `owner.__dict__` (a
        no-op when `owner` already declares its own instance, since it is
        then found there directly) so each owner gets its own config.
        """
        config = owner.__dict__.get("__RESOURCE_CONFIG__")
        if config is None:
            # The list model is not copied: an inherited one is typed for the
            # parent (e.g. `PodList` for `class MyPod(Pod)`), so `list()`
            # would return parent instances. `_fill_from` builds one for
            # `owner` instead.
            config = ResourceConfig(
                version=self._version,
                kind=self._kind,
                plural=self._plural,
                scope=self._scope,
                group=self._group,
            )
            setattr(owner, "__RESOURCE_CONFIG__", config)
        return cast(Self, config._fill_from(owner))

    def _fill_from(self, owner: Type[ResourceType]) -> Self:
        """Fill in the missing values from the owner, in place."""
        if kind_field := owner.model_fields.get("kind"):
            if kind_field.default is not None:
                self._kind = kind_field.default
            else:
                return self
        if self._version is None or self._group is None:
            if api_version_field := owner.model_fields.get("api_version"):
                if api_version_field.default is not None:
                    self._version, self._group = get_version_and_group_from_api_version(
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
            self._plural = guess_plural(self._kind)
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
    from kubex_core.models.list_entity import ListEntity
    from kubex_core.models.metadata import ListMetadata
    from kubex_core.models.types import NullAsEmptyList

    kind = f"{resource_config.kind}List"
    list_model = create_model(
        kind,
        api_version=(Literal[resource_config.api_version], resource_config.api_version),  # type: ignore[arg-type]  # ty: ignore[invalid-type-form]
        kind=(Literal[kind], kind),  # type: ignore[arg-type]  # ty: ignore[invalid-type-form]
        metadata=(ListMetadata, ...),
        items=(NullAsEmptyList[single_model], ...),  # type: ignore[valid-type]  # ty: ignore[invalid-type-form]
        __base__=ListEntity[single_model],  # type: ignore[valid-type]  # ty: ignore[invalid-type-form]
    )
    # pydantic.create_model's return type is `type[BaseModel]`; we know the
    # __base__ narrows it to ListEntity[ResourceType], but mypy cannot prove it.
    return cast("Type[ListEntity[ResourceType]]", list_model)


# Kinds whose resource name is not a regular English plural. Matched against
# the lowercased kind's suffix, so `FooEndpoints` stays `fooendpoints` too
# (mirrors apimachinery's `UnsafeGuessKindToResource`).
_UNPLURALIZED_SUFFIXES = ("endpoints",)
_VOWELS = frozenset("aeiou")


def guess_plural(kind: str) -> str:
    """Guess the resource (plural) name for `kind`, e.g. `Policy` -> `policies`.

    Uses regular English rules, matching what controller-gen/kubebuilder
    produce for CRDs: `y` -> `ies` only after a consonant (`Gateway` ->
    `gateways`), `es` after `s`/`x`/`z`/`ch`/`sh` (`Mesh` -> `meshes`).
    Resources with irregular plurals should pass `plural=` explicitly.
    """
    singular = kind.lower()
    if not singular:
        raise ValueError("kind is empty")
    if singular.endswith(_UNPLURALIZED_SUFFIXES):
        return singular
    if singular.endswith("y") and len(singular) > 1 and singular[-2] not in _VOWELS:
        return f"{singular[:-1]}ies"
    if singular.endswith(("s", "x", "z", "ch", "sh")):
        return f"{singular}es"
    return f"{singular}s"


def get_version_and_group_from_api_version(api_version: str | None) -> tuple[str, str]:
    """get_version_and_group_from_api_version returns the version and group from the apiVersion."""
    if api_version is None:
        raise ValueError("api_version is not set")
    parts = api_version.split("/")
    if len(parts) == 1:
        return parts[0], "core"
    return parts[1], parts[0]
