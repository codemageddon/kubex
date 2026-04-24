from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from kubex.api._resize import (
    ResizeAccessor,
    _ResizeDescriptor,
)
from kubex.api.api import Api
from kubex.k8s.v1_35.core.v1.config_map import ConfigMap
from kubex.k8s.v1_35.core.v1.pod import Pod


def _make_api(resource_type: type) -> Api:  # type: ignore[type-arg]
    client = MagicMock()
    return Api(resource_type, client=client, namespace="default")


def test_resize_descriptor_returns_accessor_for_pod() -> None:
    api = _make_api(Pod)
    result = _ResizeDescriptor().__get__(api, type(api))
    assert isinstance(result, ResizeAccessor)


def test_resize_descriptor_raises_for_config_map() -> None:
    api = _make_api(ConfigMap)
    with pytest.raises(NotImplementedError, match="Resize"):
        _ResizeDescriptor().__get__(api, type(api))


def test_resize_descriptor_returns_self_for_class_access() -> None:
    descriptor = _ResizeDescriptor()
    result = descriptor.__get__(None, Api)
    assert result is descriptor


def test_resize_accessor_via_api_property_for_pod() -> None:
    api = _make_api(Pod)
    assert isinstance(api.resize, ResizeAccessor)


def test_resize_accessor_via_api_property_raises_for_config_map() -> None:
    api = _make_api(ConfigMap)
    with pytest.raises(NotImplementedError, match="Resize"):
        api.resize
