from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from kubex.api._eviction import EvictionAccessor, _EvictionDescriptor
from kubex.api.api import Api
from kubex.k8s.v1_35.apps.v1.deployment import Deployment
from kubex.k8s.v1_35.core.v1.pod import Pod


def _make_api(resource_type: type) -> Api:  # type: ignore[type-arg]
    client = MagicMock()
    return Api(resource_type, client=client, namespace="default")


def test_eviction_descriptor_returns_accessor_for_pod() -> None:
    api = _make_api(Pod)
    result = _EvictionDescriptor().__get__(api, type(api))
    assert isinstance(result, EvictionAccessor)


def test_eviction_descriptor_raises_for_deployment() -> None:
    api = _make_api(Deployment)
    with pytest.raises(NotImplementedError, match="Eviction"):
        _EvictionDescriptor().__get__(api, type(api))


def test_eviction_descriptor_returns_self_for_class_access() -> None:
    descriptor = _EvictionDescriptor()
    result = descriptor.__get__(None, Api)
    assert result is descriptor


def test_eviction_accessor_via_api_property_for_pod() -> None:
    api = _make_api(Pod)
    assert isinstance(api.eviction, EvictionAccessor)


def test_eviction_accessor_via_api_property_raises_for_deployment() -> None:
    api = _make_api(Deployment)
    with pytest.raises(NotImplementedError, match="Eviction"):
        api.eviction
