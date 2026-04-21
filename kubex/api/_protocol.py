from types import EllipsisType
from typing import Protocol, Type

from kubex.client.client import BaseClient
from kubex.core.params import NamespaceTypes, Timeout, TimeoutTypes
from kubex.core.request import Request
from kubex.core.request_builder.builder import RequestBuilder
from kubex_core.models.typing import ResourceType

ApiNamespaceTypes = NamespaceTypes | EllipsisType
ApiRequestTimeoutTypes = TimeoutTypes | EllipsisType


def apply_request_timeout(request: Request, value: ApiRequestTimeoutTypes) -> Request:
    """Apply a per-call ``request_timeout`` to a ``Request``.

    ``Ellipsis`` (the default) leaves the request untouched so the client's
    configured default applies. ``None`` explicitly disables the timeout.
    Any other value is normalized via :func:`Timeout.coerce`.
    """
    if value is Ellipsis:
        return request
    request.timeout = Timeout.coerce(value)
    return request


class ApiProtocol(Protocol[ResourceType]):
    _resource: Type[ResourceType]
    _client: BaseClient
    _request_builder: RequestBuilder

    def _ensure_required_namespace(
        self, namespace: ApiNamespaceTypes
    ) -> NamespaceTypes: ...

    def _ensure_optional_namespace(
        self, namespace: ApiNamespaceTypes
    ) -> NamespaceTypes: ...
