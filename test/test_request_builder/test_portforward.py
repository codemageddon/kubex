from __future__ import annotations

import pytest

from kubex.core.params import PortForwardOptions, Timeout
from kubex.core.request_builder.builder import RequestBuilder


def _options(*ports: int) -> PortForwardOptions:
    return PortForwardOptions(ports=list(ports))


def test_portforward_request_method(ns_builder: RequestBuilder) -> None:
    req = ns_builder.portforward_request("my-pod", "default", _options(8080))
    assert req.method == "GET"


def test_portforward_request_url(ns_builder: RequestBuilder) -> None:
    req = ns_builder.portforward_request("my-pod", "default", _options(8080))
    assert req.url == "/api/v1/namespaces/default/pods/my-pod/portforward"


def test_portforward_request_uses_query_param_pairs(ns_builder: RequestBuilder) -> None:
    req = ns_builder.portforward_request("my-pod", "default", _options(8080))
    assert req.query_param_pairs is not None
    assert req.query_params is None


def test_portforward_request_single_port(ns_builder: RequestBuilder) -> None:
    req = ns_builder.portforward_request("my-pod", "default", _options(8080))
    assert req.query_param_pairs == [("ports", "8080")]


def test_portforward_request_multiple_ports_in_order(
    ns_builder: RequestBuilder,
) -> None:
    req = ns_builder.portforward_request("my-pod", "default", _options(8080, 9090))
    assert req.query_param_pairs == [("ports", "8080"), ("ports", "9090")]


def test_portforward_request_port_ordering_preserved(
    ns_builder: RequestBuilder,
) -> None:
    req = ns_builder.portforward_request("my-pod", "default", _options(9090, 8080, 443))
    assert req.query_param_pairs == [
        ("ports", "9090"),
        ("ports", "8080"),
        ("ports", "443"),
    ]


def test_portforward_request_no_body(ns_builder: RequestBuilder) -> None:
    req = ns_builder.portforward_request("my-pod", "default", _options(8080))
    assert req.body is None


def test_portforward_request_no_headers(ns_builder: RequestBuilder) -> None:
    req = ns_builder.portforward_request("my-pod", "default", _options(8080))
    assert req.headers is None


def test_portforward_request_cluster_scoped_raises(
    cluster_builder: RequestBuilder,
) -> None:
    with pytest.raises(ValueError, match="namespace-scoped"):
        cluster_builder.portforward_request("my-node", None, _options(8080))


def test_portforward_request_namespace_none_raises(ns_builder: RequestBuilder) -> None:
    with pytest.raises(ValueError, match="namespace is required"):
        ns_builder.portforward_request("my-pod", None, _options(8080))


_TIMEOUT_OBJECT = Timeout(total=120, read=60)
_TIMEOUT_CASES = [
    pytest.param(..., ..., id="default_ellipsis"),
    pytest.param(30, Timeout(total=30), id="passthrough"),
    pytest.param(None, None, id="none"),
    pytest.param(_TIMEOUT_OBJECT, _TIMEOUT_OBJECT, id="object"),
]


@pytest.mark.parametrize("request_timeout,expected", _TIMEOUT_CASES)
def test_portforward_request_timeout(
    ns_builder: RequestBuilder,
    request_timeout: object,
    expected: object,
) -> None:
    kwargs = {} if request_timeout is ... else {"request_timeout": request_timeout}
    req = ns_builder.portforward_request(
        "my-pod",
        "default",
        _options(8080),
        **kwargs,  # type: ignore[arg-type]
    )
    if expected is ...:
        assert req.timeout is Ellipsis
    elif expected is None:
        assert req.timeout is None
    elif isinstance(expected, Timeout):
        assert req.timeout == expected
