from __future__ import annotations

import json
from http import HTTPStatus

import pytest

from kubex.client.client import handle_request_error
from kubex.core.exceptions import (
    BadRequest,
    Conflict,
    Forbidden,
    Gone,
    KubexApiError,
    KubexClientException,
    KubexException,
    MethodNotAllowed,
    NotFound,
    Unauthorized,
    UnprocessableEntity,
)
from kubex.core.response import HeadersWrapper, Response
from kubex_core.models.status import Status


class _TestHeaders:
    """Minimal multi-value headers that exposes get_all (matching aiohttp)."""

    def __init__(self, pairs: list[tuple[str, str]]) -> None:
        self._pairs = pairs

    def get_all(self, key: str) -> list[str]:
        return [v for k, v in self._pairs if k.lower() == key.lower()]

    def keys(self) -> list[str]:
        return list({k for k, _ in self._pairs})

    def __getitem__(self, key: str) -> str:
        for k, v in self._pairs:
            if k.lower() == key.lower():
                return v
        raise KeyError(key)

    def __iter__(self):  # type: ignore[no-untyped-def]
        return iter(self.keys())

    def __len__(self) -> int:
        return len(self._pairs)


def _make_response(
    status_code: int,
    text: str = "",
    content_type: str | None = None,
) -> Response:
    pairs: list[tuple[str, str]] = []
    if content_type is not None:
        pairs.append(("content-type", content_type))
    return Response(
        content=text.encode("utf-8"),
        headers=HeadersWrapper(_TestHeaders(pairs)),  # type: ignore[arg-type]
        status_code=status_code,
    )


def _make_status_json(
    code: int,
    message: str = "something went wrong",
    reason: str = "BadRequest",
) -> str:
    return json.dumps(
        {
            "apiVersion": "v1",
            "kind": "Status",
            "metadata": {},
            "status": "Failure",
            "message": message,
            "reason": reason,
            "code": code,
        }
    )


STATUS_EXCEPTION_PAIRS = [
    (HTTPStatus.BAD_REQUEST, BadRequest),
    (HTTPStatus.UNAUTHORIZED, Unauthorized),
    (HTTPStatus.FORBIDDEN, Forbidden),
    (HTTPStatus.NOT_FOUND, NotFound),
    (HTTPStatus.METHOD_NOT_ALLOWED, MethodNotAllowed),
    (HTTPStatus.CONFLICT, Conflict),
    (HTTPStatus.GONE, Gone),
    (HTTPStatus.UNPROCESSABLE_ENTITY, UnprocessableEntity),
]

_STATUS_IDS = lambda v: v.name if isinstance(v, HTTPStatus) else ""  # noqa: E731


@pytest.mark.parametrize(
    ("status_code", "exc_class"),
    STATUS_EXCEPTION_PAIRS,
    ids=_STATUS_IDS,
)
def test_handle_request_error_raises_correct_exception(
    status_code: HTTPStatus,
    exc_class: type[KubexApiError],  # type: ignore[type-arg]
) -> None:
    response = _make_response(status_code)
    with pytest.raises(exc_class):
        handle_request_error(response)


@pytest.mark.parametrize(
    ("status_code", "exc_class"),
    STATUS_EXCEPTION_PAIRS,
    ids=_STATUS_IDS,
)
def test_handle_request_error_json_content_parsed_as_status(
    status_code: HTTPStatus,
    exc_class: type[KubexApiError],  # type: ignore[type-arg]
) -> None:
    body = _make_status_json(status_code, message="test error", reason="TestReason")
    response = _make_response(status_code, text=body, content_type="application/json")
    with pytest.raises(exc_class) as exc_info:
        handle_request_error(response)
    assert isinstance(exc_info.value.content, Status)
    assert exc_info.value.content.message == "test error"
    assert exc_info.value.content.reason == "TestReason"
    assert exc_info.value.content.code == int(status_code)


@pytest.mark.parametrize(
    ("status_code", "exc_class"),
    [
        (HTTPStatus.BAD_REQUEST, BadRequest),
        (HTTPStatus.NOT_FOUND, NotFound),
    ],
    ids=lambda v: v.name if isinstance(v, HTTPStatus) else "",
)
def test_handle_request_error_plain_text_content(
    status_code: HTTPStatus,
    exc_class: type[KubexApiError],  # type: ignore[type-arg]
) -> None:
    response = _make_response(
        status_code, text="plain error message", content_type="text/plain"
    )
    with pytest.raises(exc_class) as exc_info:
        handle_request_error(response)
    assert exc_info.value.content == "plain error message"
    assert isinstance(exc_info.value.content, str)


@pytest.mark.parametrize(
    "content_type",
    [
        "application/json",
        "application/json; charset=utf-8",
        "application/json;charset=utf-8",
    ],
    ids=["plain", "charset-space", "charset-nospace"],
)
def test_handle_request_error_json_content_type_with_params(
    content_type: str,
) -> None:
    body = _make_status_json(404, message="not found", reason="NotFound")
    response = _make_response(
        HTTPStatus.NOT_FOUND, text=body, content_type=content_type
    )
    with pytest.raises(NotFound) as exc_info:
        handle_request_error(response)
    assert isinstance(exc_info.value.content, Status)
    assert exc_info.value.content.message == "not found"


def test_handle_request_error_json_content_type_but_invalid_json() -> None:
    response = _make_response(
        HTTPStatus.BAD_REQUEST,
        text="not valid json",
        content_type="application/json",
    )
    with pytest.raises(BadRequest) as exc_info:
        handle_request_error(response)
    assert exc_info.value.content == "not valid json"
    assert isinstance(exc_info.value.content, str)


def test_handle_request_error_no_content_type_header() -> None:
    response = _make_response(HTTPStatus.NOT_FOUND, text="some text")
    with pytest.raises(NotFound) as exc_info:
        handle_request_error(response)
    assert exc_info.value.content == "some text"
    assert isinstance(exc_info.value.content, str)


def test_handle_request_error_unknown_status_code_valid_http() -> None:
    response = _make_response(HTTPStatus.SERVICE_UNAVAILABLE, text="service down")
    with pytest.raises(KubexApiError) as exc_info:
        handle_request_error(response)
    assert exc_info.value.status == HTTPStatus.SERVICE_UNAVAILABLE
    assert exc_info.value.content == "service down"


def test_handle_request_error_unknown_status_code_invalid() -> None:
    response = _make_response(999, text="weird error")
    with pytest.raises(KubexApiError) as exc_info:
        handle_request_error(response)
    assert exc_info.value.status == HTTPStatus.INTERNAL_SERVER_ERROR
    assert exc_info.value.content == "weird error"


def test_handle_request_error_unknown_status_code_not_in_known_map() -> None:
    response = _make_response(HTTPStatus.TOO_MANY_REQUESTS, text="rate limited")
    with pytest.raises(KubexApiError) as exc_info:
        handle_request_error(response)
    assert exc_info.value.status == HTTPStatus.TOO_MANY_REQUESTS
    assert exc_info.value.content == "rate limited"


@pytest.mark.parametrize(
    "base",
    [KubexApiError, KubexClientException, KubexException, Exception],
    ids=lambda v: v.__name__,
)
def test_exception_hierarchy(base: type[BaseException]) -> None:
    assert issubclass(NotFound, base)


def test_exception_attributes_accessible() -> None:
    body = _make_status_json(404, message="pod not found", reason="NotFound")
    response = _make_response(
        HTTPStatus.NOT_FOUND, text=body, content_type="application/json"
    )
    with pytest.raises(NotFound) as exc_info:
        handle_request_error(response)
    err = exc_info.value
    assert isinstance(err.content, Status)
    assert err.content.message == "pod not found"
    assert err.content.reason == "NotFound"
    assert err.content.status == "Failure"
    assert err.content.code == 404


@pytest.mark.parametrize(
    ("exc_class", "expected_status"),
    [
        (BadRequest, HTTPStatus.BAD_REQUEST),
        (Unauthorized, HTTPStatus.UNAUTHORIZED),
        (Forbidden, HTTPStatus.FORBIDDEN),
        (NotFound, HTTPStatus.NOT_FOUND),
        (MethodNotAllowed, HTTPStatus.METHOD_NOT_ALLOWED),
        (Conflict, HTTPStatus.CONFLICT),
        (Gone, HTTPStatus.GONE),
        (UnprocessableEntity, HTTPStatus.UNPROCESSABLE_ENTITY),
    ],
    ids=lambda v: v.__name__ if isinstance(v, type) else "",
)
def test_exception_class_status_attribute(
    exc_class: type[KubexApiError],  # type: ignore[type-arg]
    expected_status: HTTPStatus,
) -> None:
    assert exc_class.status == expected_status


@pytest.mark.parametrize(
    ("status_code", "exc_class"),
    STATUS_EXCEPTION_PAIRS,
    ids=_STATUS_IDS,
)
def test_handle_request_error_instance_status_matches_http_code(
    status_code: HTTPStatus,
    exc_class: type[KubexApiError],  # type: ignore[type-arg]
) -> None:
    response = _make_response(status_code, text="error")
    with pytest.raises(exc_class) as exc_info:
        handle_request_error(response)
    assert exc_info.value.status == status_code


def test_second_level_subclass_inherits_status() -> None:
    """A subclass of NotFound should inherit NOT_FOUND, not fall back to BAD_REQUEST."""

    class CustomNotFound(NotFound[str]):
        pass

    err = CustomNotFound(content="gone")
    assert err.status == HTTPStatus.NOT_FOUND


def test_second_level_subclass_explicit_status_override() -> None:
    """A subclass can still override the status explicitly."""

    class CustomError(NotFound[str]):
        status = HTTPStatus.IM_A_TEAPOT

    err = CustomError(content="teapot")
    assert err.status == HTTPStatus.IM_A_TEAPOT


def test_second_level_subclass_status_via_constructor() -> None:
    """Constructor status= kwarg takes precedence over class variable."""

    class CustomNotFound(NotFound[str]):
        pass

    err = CustomNotFound(content="gone", status=HTTPStatus.FORBIDDEN)
    assert err.status == HTTPStatus.FORBIDDEN
