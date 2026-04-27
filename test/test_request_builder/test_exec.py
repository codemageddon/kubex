from __future__ import annotations

import pytest

from kubex.core.params import ExecOptions, Timeout
from kubex.core.request_builder.builder import RequestBuilder


def _basic_options() -> ExecOptions:
    return ExecOptions(command=["ls", "-la"])


def test_exec_request_method(ns_builder: RequestBuilder) -> None:
    req = ns_builder.exec_request("my-pod", "default", _basic_options())
    assert req.method == "GET"


def test_exec_request_url_namespaced(ns_builder: RequestBuilder) -> None:
    req = ns_builder.exec_request("my-pod", "default", _basic_options())
    assert req.url == "/api/v1/namespaces/default/pods/my-pod/exec"


def test_exec_request_query_params_command_repeated(ns_builder: RequestBuilder) -> None:
    opts = ExecOptions(command=["sh", "-c", "echo hi"])
    req = ns_builder.exec_request("my-pod", "default", opts)
    assert req.query_param_pairs is not None
    command_params = [(k, v) for k, v in req.query_param_pairs if k == "command"]
    assert command_params == [
        ("command", "sh"),
        ("command", "-c"),
        ("command", "echo hi"),
    ]


def test_exec_request_query_params_default_flags(ns_builder: RequestBuilder) -> None:
    req = ns_builder.exec_request("my-pod", "default", _basic_options())
    assert req.query_param_pairs == [
        ("command", "ls"),
        ("command", "-la"),
        ("stdin", "false"),
        ("stdout", "true"),
        ("stderr", "true"),
        ("tty", "false"),
    ]


def test_exec_request_query_params_with_container(ns_builder: RequestBuilder) -> None:
    opts = ExecOptions(command=["true"], container="nginx")
    req = ns_builder.exec_request("my-pod", "default", opts)
    assert ("container", "nginx") in (req.query_param_pairs or [])


def test_exec_request_query_params_without_container(
    ns_builder: RequestBuilder,
) -> None:
    req = ns_builder.exec_request("my-pod", "default", _basic_options())
    assert req.query_param_pairs is not None
    assert all(k != "container" for k, _ in req.query_param_pairs)


def test_exec_request_query_params_all_flags_true(ns_builder: RequestBuilder) -> None:
    opts = ExecOptions(
        command=["sh"],
        container="app",
        stdin=True,
        stdout=True,
        stderr=True,
        tty=True,
    )
    req = ns_builder.exec_request("my-pod", "default", opts)
    assert req.query_param_pairs == [
        ("command", "sh"),
        ("container", "app"),
        ("stdin", "true"),
        ("stdout", "true"),
        ("stderr", "true"),
        ("tty", "true"),
    ]


def test_exec_request_no_body(ns_builder: RequestBuilder) -> None:
    req = ns_builder.exec_request("my-pod", "default", _basic_options())
    assert req.body is None


def test_exec_request_no_headers(ns_builder: RequestBuilder) -> None:
    req = ns_builder.exec_request("my-pod", "default", _basic_options())
    assert req.headers is None


def test_exec_request_cluster_scoped_resource_raises(
    cluster_builder: RequestBuilder,
) -> None:
    with pytest.raises(ValueError, match="namespace-scoped"):
        cluster_builder.exec_request("my-node", None, _basic_options())


def test_exec_request_namespace_none_raises(ns_builder: RequestBuilder) -> None:
    with pytest.raises(ValueError, match="namespace is required"):
        ns_builder.exec_request("my-pod", None, _basic_options())


_TIMEOUT_OBJECT = Timeout(total=120, read=60)
_TIMEOUT_CASES = [
    pytest.param(..., ..., id="default_ellipsis"),
    pytest.param(30, Timeout(total=30), id="passthrough"),
    pytest.param(None, None, id="none"),
    pytest.param(_TIMEOUT_OBJECT, _TIMEOUT_OBJECT, id="object"),
]


@pytest.mark.parametrize("request_timeout,expected", _TIMEOUT_CASES)
def test_exec_request_timeout(
    ns_builder: RequestBuilder,
    request_timeout: object,
    expected: object,
) -> None:
    kwargs = {} if request_timeout is ... else {"request_timeout": request_timeout}
    req = ns_builder.exec_request(
        "my-pod",
        "default",
        _basic_options(),
        **kwargs,  # type: ignore[arg-type]
    )
    if expected is ...:
        assert req.timeout is Ellipsis
    elif expected is None:
        assert req.timeout is None
    elif isinstance(expected, Timeout):
        assert req.timeout == expected
