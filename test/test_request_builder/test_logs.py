from __future__ import annotations

import pytest

from kubex.core.params import LogOptions, Timeout
from kubex.core.request_builder.builder import RequestBuilder


def test_logs_method(ns_builder: RequestBuilder) -> None:
    req = ns_builder.logs("my-pod", "default", LogOptions())
    assert req.method == "GET"


def test_logs_url_ends_with_log(ns_builder: RequestBuilder) -> None:
    req = ns_builder.logs("my-pod", "default", LogOptions())
    assert req.url == "/api/v1/namespaces/default/pods/my-pod/log"


def test_logs_url_cluster_scoped(cluster_builder: RequestBuilder) -> None:
    req = cluster_builder.logs("my-node", None, LogOptions())
    assert req.url == "/api/v1/nodes/my-node/log"


def test_logs_query_params_default(ns_builder: RequestBuilder) -> None:
    req = ns_builder.logs("my-pod", "default", LogOptions())
    assert req.query_params is None


_SINGLE_QUERY_PARAM_CASES = [
    pytest.param(LogOptions(container="nginx"), {"container": "nginx"}, id="container"),
    pytest.param(
        LogOptions(since_seconds=3600), {"sinceSeconds": "3600"}, id="since_seconds"
    ),
    pytest.param(LogOptions(tail_lines=100), {"tailLines": "100"}, id="tail_lines"),
    pytest.param(LogOptions(timestamps=True), {"timestamps": "true"}, id="timestamps"),
    pytest.param(LogOptions(previous=True), {"previous": "true"}, id="previous"),
    pytest.param(
        LogOptions(limit_bytes=1024), {"limitBytes": "1024"}, id="limit_bytes"
    ),
    pytest.param(LogOptions(pretty=True), {"pretty": "true"}, id="pretty"),
]


@pytest.mark.parametrize("opts,expected_params", _SINGLE_QUERY_PARAM_CASES)
def test_logs_query_param(
    ns_builder: RequestBuilder,
    opts: LogOptions,
    expected_params: dict[str, str],
) -> None:
    req = ns_builder.logs("my-pod", "default", opts)
    assert req.query_params == expected_params


def test_logs_query_params_all(ns_builder: RequestBuilder) -> None:
    opts = LogOptions(
        container="nginx",
        limit_bytes=2048,
        pretty=True,
        previous=True,
        since_seconds=600,
        tail_lines=50,
        timestamps=True,
    )
    req = ns_builder.logs("my-pod", "default", opts)
    assert req.query_params == {
        "container": "nginx",
        "limitBytes": "2048",
        "pretty": "true",
        "previous": "true",
        "sinceSeconds": "600",
        "tailLines": "50",
        "timestamps": "true",
    }


_TIMEOUT_CASES = [
    pytest.param(..., ..., id="default_ellipsis"),
    pytest.param(30, Timeout(total=30), id="passthrough"),
    pytest.param(None, None, id="none"),
]

_TIMEOUT_OBJECT = Timeout(total=120, read=60)
_TIMEOUT_CASES_WITH_OBJECT = [
    *_TIMEOUT_CASES,
    pytest.param(_TIMEOUT_OBJECT, _TIMEOUT_OBJECT, id="object"),
]


@pytest.mark.parametrize("request_timeout,expected", _TIMEOUT_CASES_WITH_OBJECT)
def test_logs_timeout(
    ns_builder: RequestBuilder,
    request_timeout: object,
    expected: object,
) -> None:
    kwargs = {} if request_timeout is ... else {"request_timeout": request_timeout}
    req = ns_builder.logs("my-pod", "default", LogOptions(), **kwargs)  # type: ignore[arg-type]
    if expected is ...:
        assert req.timeout is Ellipsis
    elif expected is None:
        assert req.timeout is None
    elif isinstance(expected, Timeout):
        assert req.timeout == expected


def test_stream_logs_method(ns_builder: RequestBuilder) -> None:
    req = ns_builder.stream_logs("my-pod", "default", LogOptions())
    assert req.method == "GET"


def test_stream_logs_url_ends_with_log(ns_builder: RequestBuilder) -> None:
    req = ns_builder.stream_logs("my-pod", "default", LogOptions())
    assert req.url == "/api/v1/namespaces/default/pods/my-pod/log"


def test_stream_logs_url_cluster_scoped(cluster_builder: RequestBuilder) -> None:
    req = cluster_builder.stream_logs("my-node", None, LogOptions())
    assert req.url == "/api/v1/nodes/my-node/log"


def test_stream_logs_follow_true_with_default_options(
    ns_builder: RequestBuilder,
) -> None:
    req = ns_builder.stream_logs("my-pod", "default", LogOptions())
    assert req.query_params is not None
    assert req.query_params["follow"] == "true"


def test_stream_logs_follow_true_only_param_when_no_options(
    ns_builder: RequestBuilder,
) -> None:
    req = ns_builder.stream_logs("my-pod", "default", LogOptions())
    assert req.query_params == {"follow": "true"}


def test_stream_logs_follow_merged_with_options(
    ns_builder: RequestBuilder,
) -> None:
    opts = LogOptions(container="nginx", tail_lines=50)
    req = ns_builder.stream_logs("my-pod", "default", opts)
    assert req.query_params == {
        "container": "nginx",
        "tailLines": "50",
        "follow": "true",
    }


def test_stream_logs_follow_merged_with_all_options(
    ns_builder: RequestBuilder,
) -> None:
    opts = LogOptions(
        container="sidecar",
        limit_bytes=4096,
        pretty=False,
        previous=False,
        since_seconds=120,
        tail_lines=200,
        timestamps=True,
    )
    req = ns_builder.stream_logs("my-pod", "default", opts)
    assert req.query_params == {
        "container": "sidecar",
        "limitBytes": "4096",
        "pretty": "false",
        "previous": "false",
        "sinceSeconds": "120",
        "tailLines": "200",
        "timestamps": "true",
        "follow": "true",
    }


@pytest.mark.parametrize("request_timeout,expected", _TIMEOUT_CASES)
def test_stream_logs_timeout(
    ns_builder: RequestBuilder,
    request_timeout: object,
    expected: object,
) -> None:
    kwargs = {} if request_timeout is ... else {"request_timeout": request_timeout}
    req = ns_builder.stream_logs("my-pod", "default", LogOptions(), **kwargs)  # type: ignore[arg-type]
    if expected is ...:
        assert req.timeout is Ellipsis
    elif expected is None:
        assert req.timeout is None
    elif isinstance(expected, Timeout):
        assert req.timeout == expected
