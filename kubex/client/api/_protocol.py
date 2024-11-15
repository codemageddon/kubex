from typing import Protocol, Type

from kubex.client.client import Client
from kubex.core.request_builder.builder import RequestBuilder
from kubex.models.typing import ResourceType


class ApiProtocol(Protocol[ResourceType]):
    _resource: Type[ResourceType]
    _client: Client
    _request_builder: RequestBuilder
    _namespace: str | None

    def _check_namespace(self) -> None: ...
