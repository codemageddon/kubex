from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from kubex.api._scale import ScaleAccessor, _ScaleDescriptor
from kubex.api.api import Api
from kubex.k8s.v1_35.apps.v1.deployment import Deployment
from kubex.k8s.v1_35.core.v1.pod import Pod


def _make_api(resource_type: type) -> Api:  # type: ignore[type-arg]
    client = MagicMock()
    return Api(resource_type, client=client, namespace="default")


def test_scale_descriptor_returns_accessor_for_deployment() -> None:
    api = _make_api(Deployment)
    result = _ScaleDescriptor().__get__(api, type(api))
    assert isinstance(result, ScaleAccessor)


def test_scale_descriptor_raises_for_pod() -> None:
    api = _make_api(Pod)
    with pytest.raises(NotImplementedError, match="Scale"):
        _ScaleDescriptor().__get__(api, type(api))


def test_scale_descriptor_returns_self_for_class_access() -> None:
    descriptor = _ScaleDescriptor()
    result = descriptor.__get__(None, Api)
    assert result is descriptor


def test_scale_accessor_via_api_property_for_deployment() -> None:
    api = _make_api(Deployment)
    assert isinstance(api.scale, ScaleAccessor)


def test_scale_accessor_via_api_property_raises_for_pod() -> None:
    api = _make_api(Pod)
    with pytest.raises(NotImplementedError, match="Scale"):
        api.scale
