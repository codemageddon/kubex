from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from kubex.api._status import StatusAccessor, _StatusDescriptor
from kubex.api.api import Api
from kubex.k8s.v1_35.core.v1.config_map import ConfigMap
from kubex.k8s.v1_35.core.v1.pod import Pod


def _make_api(resource_type: type) -> Api:  # type: ignore[type-arg]
    client = MagicMock()
    return Api(resource_type, client=client, namespace="default")


def test_status_descriptor_returns_accessor_for_pod() -> None:
    api = _make_api(Pod)
    result = _StatusDescriptor().__get__(api, type(api))
    assert isinstance(result, StatusAccessor)


def test_status_descriptor_raises_for_config_map() -> None:
    api = _make_api(ConfigMap)
    with pytest.raises(NotImplementedError, match="Status"):
        _StatusDescriptor().__get__(api, type(api))


def test_status_descriptor_returns_self_for_class_access() -> None:
    descriptor = _StatusDescriptor()
    result = descriptor.__get__(None, Api)
    assert result is descriptor


def test_status_accessor_via_api_property_for_pod() -> None:
    api = _make_api(Pod)
    assert isinstance(api.status, StatusAccessor)


def test_status_accessor_via_api_property_raises_for_config_map() -> None:
    api = _make_api(ConfigMap)
    with pytest.raises(NotImplementedError, match="Status"):
        api.status
