from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from kubex.api._logs import LogsAccessor, _LogsDescriptor
from kubex.api.api import Api
from kubex.k8s.v1_35.core.v1.namespace import Namespace
from kubex.k8s.v1_35.core.v1.pod import Pod


def _make_api(resource_type: type) -> Api:  # type: ignore[type-arg]
    client = MagicMock()
    return Api(resource_type, client=client)


def test_logs_descriptor_returns_accessor_for_pod() -> None:
    api = _make_api(Pod)
    result = _LogsDescriptor().__get__(api, type(api))
    assert isinstance(result, LogsAccessor)


def test_logs_descriptor_raises_for_namespace() -> None:
    api = _make_api(Namespace)
    with pytest.raises(NotImplementedError, match="Logs"):
        _LogsDescriptor().__get__(api, type(api))


def test_logs_descriptor_returns_self_for_class_access() -> None:
    descriptor = _LogsDescriptor()
    result = descriptor.__get__(None, Api)
    assert result is descriptor


def test_logs_accessor_via_api_property_for_pod() -> None:
    api = _make_api(Pod)
    assert isinstance(api.logs, LogsAccessor)


def test_logs_accessor_via_api_property_raises_for_namespace() -> None:
    api = _make_api(Namespace)
    with pytest.raises(NotImplementedError, match="Logs"):
        api.logs
