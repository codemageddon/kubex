from __future__ import annotations

from types import EllipsisType
from typing import Any, ClassVar, Protocol, Type

from kubex.client.client import BaseClient
from kubex.core.params import NamespaceTypes, TimeoutTypes
from kubex.core.request_builder.builder import RequestBuilder
from kubex_core.models.resource_config import Scope
from kubex_core.models.typing import ResourceType

ApiNamespaceTypes = NamespaceTypes | EllipsisType
ApiRequestTimeoutTypes = TimeoutTypes | EllipsisType


class SubresourceNotAvailable:
    __slots__ = ()


def get_namespace(
    namespace: ApiNamespaceTypes, default: NamespaceTypes
) -> NamespaceTypes:
    if namespace is Ellipsis:
        return default
    return namespace


def ensure_required_namespace(
    namespace: ApiNamespaceTypes,
    default: NamespaceTypes,
    scope: Scope,
) -> NamespaceTypes:
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
    _namespace = get_namespace(namespace, default)
    if scope == Scope.CLUSTER and _namespace is not None:
        raise ValueError("Namespace is not supported for cluster-scoped resources")
    return _namespace


class ApiProtocol(Protocol[ResourceType]):
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
        )
        if hasattr(self, "_attr_name"):
            instance.__dict__[self._attr_name] = accessor
        return accessor
