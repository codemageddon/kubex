from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from kubex.api._ephemeral_containers import (
    EphemeralContainersAccessor,
    _EphemeralContainersDescriptor,
)
from kubex.api.api import Api
from kubex.k8s.v1_35.core.v1.config_map import ConfigMap
from kubex.k8s.v1_35.core.v1.pod import Pod


def _make_api(resource_type: type) -> Api:  # type: ignore[type-arg]
    client = MagicMock()
    return Api(resource_type, client=client, namespace="default")


def test_ephemeral_containers_descriptor_returns_accessor_for_pod() -> None:
    api = _make_api(Pod)
    result = _EphemeralContainersDescriptor().__get__(api, type(api))
    assert isinstance(result, EphemeralContainersAccessor)


def test_ephemeral_containers_descriptor_raises_for_config_map() -> None:
    api = _make_api(ConfigMap)
    with pytest.raises(NotImplementedError, match="Ephemeral"):
        _EphemeralContainersDescriptor().__get__(api, type(api))


def test_ephemeral_containers_descriptor_returns_self_for_class_access() -> None:
    descriptor = _EphemeralContainersDescriptor()
    result = descriptor.__get__(None, Api)
    assert result is descriptor


def test_ephemeral_containers_accessor_via_api_property_for_pod() -> None:
    api = _make_api(Pod)
    assert isinstance(api.ephemeral_containers, EphemeralContainersAccessor)


def test_ephemeral_containers_accessor_via_api_property_raises_for_config_map() -> None:
    api = _make_api(ConfigMap)
    with pytest.raises(NotImplementedError, match="Ephemeral"):
        api.ephemeral_containers
