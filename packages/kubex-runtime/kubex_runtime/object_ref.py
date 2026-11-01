from __future__ import annotations

from dataclasses import dataclass

from kubex_core.models.base_entity import BaseEntity
from kubex_core.models.metadata import OwnerReference

# kubex names the core group "core"; Kubernetes (and kube-rs) name it ""
_CORE = "core"


def _group(group: str) -> str:
    return group or _CORE


@dataclass(frozen=True)
class ObjectRef:
    """A reference to one object, the key of stores and controllers.

    Two references are equal when they name the same object of the same kind.
    The core group may be given as "" or "core": it is kept as "core".
    """

    group: str
    kind: str
    name: str
    namespace: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "group", _group(self.group))

    @classmethod
    def of(
        cls, model: type[BaseEntity], name: str, namespace: str | None = None
    ) -> ObjectRef:
        """Refers to the object `name` of the kind `model`."""
        config = model.__RESOURCE_CONFIG__
        return cls(group=config.group, kind=config.kind, name=name, namespace=namespace)

    @classmethod
    def from_obj(cls, obj: BaseEntity) -> ObjectRef:
        """Refers to `obj`, which must have a name."""
        name = obj.metadata.name
        if not name:
            raise ValueError(f"{type(obj).__name__} has no name")
        return cls.of(type(obj), name, obj.metadata.namespace)

    @classmethod
    def from_owner(
        cls, owner: OwnerReference, namespace: str | None = None
    ) -> ObjectRef:
        """Refers to the owner `owner` of an object.

        An owner is in its dependent's namespace, or cluster-scoped, which the
        reference does not say: pass the dependent's namespace for a namespaced
        owner kind, None for a cluster-scoped one.
        """
        # the core group's apiVersion ("v1") has no group part
        group, _, _ = owner.api_version.rpartition("/")
        return cls(group=group, kind=owner.kind, name=owner.name, namespace=namespace)

    def is_kind_of(self, model: type[BaseEntity]) -> bool:
        config = model.__RESOURCE_CONFIG__
        return self.group == _group(config.group) and self.kind == config.kind

    def __str__(self) -> str:
        kind = f"{self.kind}.{self.group}"
        if self.namespace:
            return f"{kind} {self.namespace}/{self.name}"
        return f"{kind} {self.name}"
