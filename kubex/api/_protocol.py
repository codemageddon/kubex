from types import EllipsisType
from typing import Protocol, Type

from kubex.client.client import BaseClient
from kubex.core.params import NamespaceTypes, TimeoutTypes
from kubex.core.request_builder.builder import RequestBuilder
from kubex_core.models.typing import ResourceType

ApiNamespaceTypes = NamespaceTypes | EllipsisType
ApiRequestTimeoutTypes = TimeoutTypes | EllipsisType


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
