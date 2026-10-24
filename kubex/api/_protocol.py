from __future__ import annotations

from types import EllipsisType
from typing import Any, ClassVar, Protocol, Type

from kubex.client.client import BaseClient
from kubex.core.params import NamespaceTypes, TimeoutTypes
from kubex.core.request_builder.builder import RequestBuilder
from kubex_core.models.resource_config import Scope
from kubex_core.models.typing import ResourceType

ApiNamespaceTypes = NamespaceTypes | EllipsisType
"""A per-call namespace argument: a namespace name, ``None`` (no namespace, or all
namespaces for calls that allow it), or ``...`` (omitted: use the ``Api`` default)."""
ApiRequestTimeoutTypes = TimeoutTypes | EllipsisType
"""A per-call HTTP timeout: a ``Timeout``, a number of seconds, ``None`` (no timeout),
or ``...`` (omitted: use the client default)."""


class SubresourceNotAvailable:
    """Type of a subresource accessor whose resource type does not support it.

    Type checkers see this for e.g. ``Api[Pod].scale``: it has no attributes, so
    any call on it is a type error. At runtime the attribute access raises
    ``NotImplementedError`` instead.
    """

    __slots__ = ()


def get_namespace(
    namespace: ApiNamespaceTypes, default: NamespaceTypes
) -> NamespaceTypes:
    """Resolve a per-call namespace argument against the ``Api`` default.

    Args:
        namespace: The namespace passed to the call, or ``...`` if it was omitted.
        default: The ``Api`` instance's namespace.

    Returns:
        NamespaceTypes: ``default`` if ``namespace`` was omitted, otherwise
            ``namespace`` (which may be ``None``).
    """
    if namespace is Ellipsis:
        return default
    return namespace


def ensure_required_namespace(
    namespace: ApiNamespaceTypes,
    default: NamespaceTypes,
    scope: Scope,
) -> NamespaceTypes:
    """Resolve the namespace for a call that targets a single object.

    Args:
        namespace: The namespace passed to the call, or ``...`` to use ``default``.
        default: The ``Api`` instance's namespace.
        scope: The resource's scope.

    Returns:
        NamespaceTypes: the namespace to use; ``None`` for a cluster-scoped resource.

    Raises:
        ValueError: no namespace resolves for a namespace-scoped resource, or one
            resolves for a cluster-scoped resource.
    """
    _namespace = get_namespace(namespace, default)
    if _namespace is None and scope == Scope.NAMESPACE:
        raise ValueError("Namespace is required")
    if _namespace is not None and scope == Scope.CLUSTER:
        raise ValueError("Namespace is not supported for cluster-scoped resources")
    return _namespace


def ensure_optional_namespace(
    namespace: ApiNamespaceTypes,
    default: NamespaceTypes,
    scope: Scope,
) -> NamespaceTypes:
    """Resolve the namespace for a call that may span namespaces.

    Used by ``list``, ``watch`` and ``delete_collection``.

    Args:
        namespace: The namespace passed to the call, or ``...`` to use ``default``.
        default: The ``Api`` instance's namespace.
        scope: The resource's scope.

    Returns:
        NamespaceTypes: the namespace to use, or ``None`` for all namespaces (always
            ``None`` for a cluster-scoped resource).

    Raises:
        ValueError: a namespace resolves for a cluster-scoped resource.
    """
    _namespace = get_namespace(namespace, default)
    if scope == Scope.CLUSTER and _namespace is not None:
        raise ValueError("Namespace is not supported for cluster-scoped resources")
    return _namespace


class ApiProtocol(Protocol[ResourceType]):
    """The parts of ``Api`` that subresource descriptors read.

    The descriptors' ``__get__`` overloads match on ``ApiProtocol[T]`` to pick the
    accessor type for resource type ``T``, or ``SubresourceNotAvailable`` when
    ``T`` lacks the matching marker interface.
    """

    _resource: Type[ResourceType]
    _client: BaseClient
    _request_builder: RequestBuilder
    _namespace: NamespaceTypes


class CachedSubresourceDescriptor:
    """Base for non-data descriptors that guard on a marker interface and cache the accessor."""

    _marker: ClassVar[type]
    _accessor_cls: ClassVar[type]
    _error_message: ClassVar[str]
    _attr_name: str

    def __set_name__(self, owner: type, name: str) -> None:
        self._attr_name = name

    def _resolve(self, instance: Any) -> Any:
        if instance is None:
            return self
        if not issubclass(instance._resource, self._marker):
            raise NotImplementedError(self._error_message)
        accessor: Any = self._accessor_cls(
            client=instance._client,
            request_builder=instance._request_builder,
            namespace=instance._namespace,
            scope=instance._resource.__RESOURCE_CONFIG__.scope,
            resource_type=instance._resource,
        )
        if hasattr(self, "_attr_name"):
            instance.__dict__[self._attr_name] = accessor
        return accessor
