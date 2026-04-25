from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from kubex.api._ephemeral_containers import (
    EphemeralContainersAccessor,
    _EphemeralContainersDescriptor,
)
from kubex.api._eviction import EvictionAccessor, _EvictionDescriptor
from kubex.api._logs import LogsAccessor, _LogsDescriptor
from kubex.api._resize import ResizeAccessor, _ResizeDescriptor
from kubex.api._scale import ScaleAccessor, _ScaleDescriptor
from kubex.api._status import StatusAccessor, _StatusDescriptor
from kubex.api.api import Api
from kubex.k8s.v1_35.apps.v1.deployment import Deployment
from kubex.k8s.v1_35.core.v1.config_map import ConfigMap
from kubex.k8s.v1_35.core.v1.namespace import Namespace
from kubex.k8s.v1_35.core.v1.pod import Pod
from kubex_core.models.interfaces import ClusterScopedEntity

_DESCRIPTOR_CASES = [
    pytest.param(
        _StatusDescriptor,
        StatusAccessor,
        Pod,
        ConfigMap,
        "status",
        "Status",
        id="status",
    ),
    pytest.param(
        _ScaleDescriptor,
        ScaleAccessor,
        Deployment,
        Pod,
        "scale",
        "Scale",
        id="scale",
    ),
    pytest.param(
        _LogsDescriptor,
        LogsAccessor,
        Pod,
        Namespace,
        "logs",
        "Logs",
        id="logs",
    ),
    pytest.param(
        _EvictionDescriptor,
        EvictionAccessor,
        Pod,
        Deployment,
        "eviction",
        "Eviction",
        id="eviction",
    ),
    pytest.param(
        _ResizeDescriptor,
        ResizeAccessor,
        Pod,
        ConfigMap,
        "resize",
        "Resize",
        id="resize",
    ),
    pytest.param(
        _EphemeralContainersDescriptor,
        EphemeralContainersAccessor,
        Pod,
        ConfigMap,
        "ephemeral_containers",
        "Ephemeral",
        id="ephemeral_containers",
    ),
]


def _make_api(resource_type: type) -> Api:  # type: ignore[type-arg]
    client = MagicMock()
    if issubclass(resource_type, ClusterScopedEntity):
        return Api(resource_type, client=client)
    return Api(resource_type, client=client, namespace="default")


@pytest.mark.parametrize(
    "descriptor_cls,accessor_cls,supported,unsupported,attr_name,error_match",
    _DESCRIPTOR_CASES,
)
def test_descriptor_returns_accessor_for_supported_resource(
    descriptor_cls: type,
    accessor_cls: type,
    supported: type,
    unsupported: type,
    attr_name: str,
    error_match: str,
) -> None:
    api = _make_api(supported)
    result = descriptor_cls().__get__(api, type(api))
    assert isinstance(result, accessor_cls)


@pytest.mark.parametrize(
    "descriptor_cls,accessor_cls,supported,unsupported,attr_name,error_match",
    _DESCRIPTOR_CASES,
)
def test_descriptor_raises_for_unsupported_resource(
    descriptor_cls: type,
    accessor_cls: type,
    supported: type,
    unsupported: type,
    attr_name: str,
    error_match: str,
) -> None:
    api = _make_api(unsupported)
    with pytest.raises(NotImplementedError, match=error_match):
        descriptor_cls().__get__(api, type(api))


@pytest.mark.parametrize(
    "descriptor_cls,accessor_cls,supported,unsupported,attr_name,error_match",
    _DESCRIPTOR_CASES,
)
def test_descriptor_returns_self_for_class_access(
    descriptor_cls: type,
    accessor_cls: type,
    supported: type,
    unsupported: type,
    attr_name: str,
    error_match: str,
) -> None:
    descriptor = descriptor_cls()
    result = descriptor.__get__(None, Api)
    assert result is descriptor


@pytest.mark.parametrize(
    "descriptor_cls,accessor_cls,supported,unsupported,attr_name,error_match",
    _DESCRIPTOR_CASES,
)
def test_accessor_via_api_property_for_supported_resource(
    descriptor_cls: type,
    accessor_cls: type,
    supported: type,
    unsupported: type,
    attr_name: str,
    error_match: str,
) -> None:
    api = _make_api(supported)
    assert isinstance(getattr(api, attr_name), accessor_cls)


@pytest.mark.parametrize(
    "descriptor_cls,accessor_cls,supported,unsupported,attr_name,error_match",
    _DESCRIPTOR_CASES,
)
def test_accessor_via_api_property_raises_for_unsupported_resource(
    descriptor_cls: type,
    accessor_cls: type,
    supported: type,
    unsupported: type,
    attr_name: str,
    error_match: str,
) -> None:
    api = _make_api(unsupported)
    with pytest.raises(NotImplementedError, match=error_match):
        getattr(api, attr_name)
