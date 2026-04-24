from __future__ import annotations

import pytest

from kubex.api import Api
from kubex.client import BaseClient
from kubex.core.exceptions import NotFound
from kubex.k8s.v1_35.core.v1.config_map import ConfigMap
from kubex_core.models.list_entity import ListEntity
from kubex_core.models.metadata import ObjectMetadata
from kubex_core.models.status import Status

_TEST_LABEL = {"kubex-test": "true"}


def _configmap(name: str, namespace: str, **data: str) -> ConfigMap:
    return ConfigMap(
        metadata=ObjectMetadata(name=name, namespace=namespace, labels=_TEST_LABEL),
        data=data or None,
    )


@pytest.mark.anyio
async def test_replace(client: BaseClient, tmp_namespace_name: str) -> None:
    api: Api[ConfigMap] = Api(ConfigMap, client=client, namespace=tmp_namespace_name)

    cm = await api.create(_configmap("replace-cm", tmp_namespace_name, key="old"))
    assert cm.data is not None
    assert cm.data["key"] == "old"

    cm.data["key"] = "new"
    result = await api.replace("replace-cm", cm)
    assert isinstance(result, ConfigMap)
    assert result.data is not None
    assert result.data["key"] == "new"

    fetched = await api.get("replace-cm")
    assert fetched.data is not None
    assert fetched.data["key"] == "new"


@pytest.mark.anyio
async def test_replace_with_dry_run(
    client: BaseClient, tmp_namespace_name: str
) -> None:
    api: Api[ConfigMap] = Api(ConfigMap, client=client, namespace=tmp_namespace_name)

    cm = await api.create(_configmap("replace-dry", tmp_namespace_name, key="original"))
    cm.data = {"key": "dry-run-value"}

    result = await api.replace("replace-dry", cm, dry_run=True)
    assert isinstance(result, ConfigMap)
    assert result.data is not None
    assert result.data["key"] == "dry-run-value"

    fetched = await api.get("replace-dry")
    assert fetched.data is not None
    assert fetched.data["key"] == "original"


@pytest.mark.anyio
async def test_replace_with_explicit_namespace(
    client: BaseClient, tmp_namespace_name: str
) -> None:
    api: Api[ConfigMap] = Api(ConfigMap, client=client)
    cm = await api.create(
        _configmap("replace-ns", tmp_namespace_name, v="1"),
        namespace=tmp_namespace_name,
    )
    cm.data = {"v": "2"}
    result = await api.replace("replace-ns", cm, namespace=tmp_namespace_name)
    assert isinstance(result, ConfigMap)
    assert result.data is not None
    assert result.data["v"] == "2"


@pytest.mark.anyio
async def test_delete_collection(client: BaseClient, tmp_namespace_name: str) -> None:
    api: Api[ConfigMap] = Api(ConfigMap, client=client, namespace=tmp_namespace_name)

    for i in range(3):
        await api.create(
            _configmap(f"dc-{i}", tmp_namespace_name, idx=str(i)),
        )

    items = await api.list(label_selector="kubex-test=true")
    assert len(items.items) >= 3

    result = await api.delete_collection(label_selector="kubex-test=true")
    assert isinstance(result, (Status, ListEntity))

    remaining = await api.list(label_selector="kubex-test=true")
    assert len(remaining.items) == 0


@pytest.mark.anyio
async def test_delete_collection_with_label_selector(
    client: BaseClient, tmp_namespace_name: str
) -> None:
    api: Api[ConfigMap] = Api(ConfigMap, client=client, namespace=tmp_namespace_name)

    keep = _configmap("dc-keep", tmp_namespace_name)
    keep.metadata.labels = {**_TEST_LABEL, "group": "keep"}
    await api.create(keep)

    remove = _configmap("dc-remove", tmp_namespace_name)
    remove.metadata.labels = {**_TEST_LABEL, "group": "remove"}
    await api.create(remove)

    result = await api.delete_collection(label_selector="group=remove")
    assert isinstance(result, (Status, ListEntity))

    kept = await api.get("dc-keep")
    assert kept.metadata.name == "dc-keep"

    with pytest.raises(NotFound):
        await api.get("dc-remove")
