import pytest

from kubex import Api, Client
from kubex.models.namespace import Namespace


@pytest.mark.anyio
async def test_list_namespaces(client: Client) -> None:
    api: Api[Namespace] = Api.all(Namespace, client=client)
    namespaces = await api.list()
    assert namespaces is not None
    assert len(namespaces.items) > 0
    assert all(isinstance(namespace, Namespace) for namespace in namespaces.items)
