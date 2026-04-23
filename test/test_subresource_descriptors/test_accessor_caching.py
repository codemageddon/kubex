from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from kubex.api._ephemeral_containers import EphemeralContainersAccessor
from kubex.api._eviction import EvictionAccessor
from kubex.api._logs import LogsAccessor
from kubex.api._resize import ResizeAccessor
from kubex.api._scale import ScaleAccessor
from kubex.api._status import StatusAccessor
from kubex.api.api import Api
from kubex.k8s.v1_35.apps.v1.deployment import Deployment
from kubex.k8s.v1_35.core.v1.pod import Pod


def _make_api(resource_type: type, **kwargs: object) -> Api:  # type: ignore[type-arg]
    client = MagicMock()
    return Api(resource_type, client=client, namespace="default", **kwargs)


@pytest.mark.parametrize(
    ("resource_type", "attr", "accessor_type"),
    [
        (Pod, "logs", LogsAccessor),
        (Pod, "status", StatusAccessor),
        (Pod, "eviction", EvictionAccessor),
        (Pod, "ephemeral_containers", EphemeralContainersAccessor),
        (Pod, "resize", ResizeAccessor),
        (Deployment, "scale", ScaleAccessor),
    ],
)
def test_accessor_is_cached_after_first_access(
    resource_type: type, attr: str, accessor_type: type
) -> None:
    api = _make_api(resource_type)
    first = getattr(api, attr)
    second = getattr(api, attr)
    assert isinstance(first, accessor_type)
    assert first is second


@pytest.mark.parametrize(
    ("resource_type", "attr"),
    [
        (Pod, "logs"),
        (Pod, "status"),
        (Pod, "eviction"),
        (Pod, "ephemeral_containers"),
        (Pod, "resize"),
        (Deployment, "scale"),
    ],
)
def test_cached_accessor_stored_in_instance_dict(
    resource_type: type, attr: str
) -> None:
    api = _make_api(resource_type)
    getattr(api, attr)
    assert attr in api.__dict__


@pytest.mark.parametrize(
    ("resource_type", "attr"),
    [
        (Pod, "logs"),
        (Pod, "status"),
        (Pod, "eviction"),
        (Pod, "ephemeral_containers"),
        (Pod, "resize"),
        (Deployment, "scale"),
    ],
)
def test_each_api_instance_gets_own_cached_accessor(
    resource_type: type, attr: str
) -> None:
    api1 = _make_api(resource_type)
    api2 = _make_api(resource_type)
    assert getattr(api1, attr) is not getattr(api2, attr)


@pytest.mark.parametrize(
    ("resource_type", "attr"),
    [
        (Pod, "logs"),
        (Pod, "status"),
        (Pod, "eviction"),
        (Pod, "ephemeral_containers"),
        (Pod, "resize"),
        (Deployment, "scale"),
        (Pod, "metadata"),
    ],
)
def test_accessor_receives_resource_type(resource_type: type, attr: str) -> None:
    api = _make_api(resource_type)
    accessor = getattr(api, attr)
    assert accessor._resource_type is resource_type
