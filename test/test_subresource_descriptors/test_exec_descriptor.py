from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from kubex.api._exec import ExecAccessor, _ExecDescriptor
from kubex.api.api import Api
from kubex.k8s.v1_35.apps.v1.deployment import Deployment
from kubex.k8s.v1_35.core.v1.config_map import ConfigMap
from kubex.k8s.v1_35.core.v1.namespace import Namespace
from kubex.k8s.v1_35.core.v1.pod import Pod


def _make_api(resource_type: type, **kwargs: object) -> Api:  # type: ignore[type-arg]
    client = MagicMock()
    return Api(resource_type, client=client, namespace="default", **kwargs)


def test_descriptor_returns_accessor_for_pod() -> None:
    api = _make_api(Pod)
    accessor = _ExecDescriptor().__get__(api, type(api))
    assert isinstance(accessor, ExecAccessor)


@pytest.mark.parametrize(
    "unsupported",
    [Deployment, ConfigMap, Namespace],
)
def test_descriptor_raises_for_unsupported_resource(unsupported: type) -> None:
    api: Api  # type: ignore[type-arg]
    if unsupported is Namespace:
        api = Api(unsupported, client=MagicMock())
    else:
        api = _make_api(unsupported)
    with pytest.raises(NotImplementedError, match="Exec"):
        _ExecDescriptor().__get__(api, type(api))


def test_descriptor_returns_self_for_class_access() -> None:
    descriptor = _ExecDescriptor()
    assert descriptor.__get__(None, Api) is descriptor


def test_accessor_via_api_property_for_pod() -> None:
    api = _make_api(Pod)
    assert isinstance(api.exec, ExecAccessor)


@pytest.mark.parametrize(
    "unsupported",
    [Deployment, ConfigMap, Namespace],
)
def test_accessor_via_api_property_raises_for_unsupported_resource(
    unsupported: type,
) -> None:
    api: Api  # type: ignore[type-arg]
    if unsupported is Namespace:
        api = Api(unsupported, client=MagicMock())
    else:
        api = _make_api(unsupported)
    with pytest.raises(NotImplementedError, match="Exec"):
        _ = api.exec


def test_exec_accessor_is_cached() -> None:
    api = _make_api(Pod)
    first = api.exec
    second = api.exec
    assert first is second


def test_cached_accessor_stored_in_instance_dict() -> None:
    api = _make_api(Pod)
    _ = api.exec
    assert "exec" in api.__dict__


def test_each_api_instance_gets_own_cached_accessor() -> None:
    api1 = _make_api(Pod)
    api2 = _make_api(Pod)
    assert api1.exec is not api2.exec


def test_accessor_receives_resource_type() -> None:
    api = _make_api(Pod)
    assert api.exec._resource_type is Pod
