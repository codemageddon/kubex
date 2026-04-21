from kubex.core.request import Request


def test_request_timeout_default_is_ellipsis() -> None:
    request = Request(method="GET", url="/api/v1/namespaces")
    assert request.timeout is Ellipsis


def test_request_timeout_repr_includes_timeout() -> None:
    request = Request(method="GET", url="/api/v1/namespaces")
    assert "timeout=" in repr(request)
