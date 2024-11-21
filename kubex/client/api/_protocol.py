from types import EllipsisType
from typing import Protocol, Type

from kubex.client.client import Client
from kubex.core.params import NamespaceTypes
from kubex.core.request_builder.builder import RequestBuilder
from kubex.models.typing import ResourceType

ApiNamespaceTypes = NamespaceTypes | EllipsisType


class ApiProtocol(Protocol[ResourceType]):
    _resource: Type[ResourceType]
    _client: Client
    _request_builder: RequestBuilder

    def _ensure_required_namespace(
        self, namespace: ApiNamespaceTypes
    ) -> NamespaceTypes: ...

    def _ensure_optional_namespace(
        self, namespace: ApiNamespaceTypes
    ) -> NamespaceTypes: ...
