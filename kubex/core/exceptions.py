from http import HTTPStatus
from typing import Any, Generic, TypeVar

from kubex_core.models.status import Status


class KubexException(Exception):
    pass


class KubexClientException(KubexException):
    pass


C = TypeVar("C", bound=str | Status)


class ConfigurationError(KubexException):
    pass


class KubexApiError(Generic[C], KubexClientException):
    status: HTTPStatus
    content: C

    def __init__(
        self,
        content: C,
        *args: Any,
        status: HTTPStatus | None = None,
    ) -> None:
        super().__init__(*args)
        if status is not None:
            self.status = status
        elif not hasattr(type(self), "status"):
            self.status = HTTPStatus.BAD_REQUEST
        self.content = content


class BadRequest(KubexApiError[C]):
    status = HTTPStatus.BAD_REQUEST


class Unauthorized(KubexApiError[C]):
    status = HTTPStatus.UNAUTHORIZED


class Forbidden(KubexApiError[C]):
    status = HTTPStatus.FORBIDDEN


class NotFound(KubexApiError[C]):
    status = HTTPStatus.NOT_FOUND


class MethodNotAllowed(KubexApiError[C]):
    status = HTTPStatus.METHOD_NOT_ALLOWED


class Conflict(KubexApiError[C]):
    status = HTTPStatus.CONFLICT


class Gone(KubexApiError[C]):
    status = HTTPStatus.GONE


class UnprocessableEntity(KubexApiError[C]):
    status = HTTPStatus.UNPROCESSABLE_ENTITY


class KubernetesError(KubexApiError[C]):
    status = HTTPStatus.INTERNAL_SERVER_ERROR


def build_exception(status_code: int, content: C) -> KubexApiError[C]:
    match status_code:
        case HTTPStatus.BAD_REQUEST:
            return BadRequest(content=content)
        case HTTPStatus.UNAUTHORIZED:
            return Unauthorized(content=content)
        case HTTPStatus.FORBIDDEN:
            return Forbidden(content=content)
        case HTTPStatus.NOT_FOUND:
            return NotFound(content=content)
        case HTTPStatus.METHOD_NOT_ALLOWED:
            return MethodNotAllowed(content=content)
        case HTTPStatus.CONFLICT:
            return Conflict(content=content)
        case HTTPStatus.GONE:
            return Gone(content=content)
        case HTTPStatus.UNPROCESSABLE_ENTITY:
            return UnprocessableEntity(content=content)
        case HTTPStatus.INTERNAL_SERVER_ERROR:
            return KubernetesError(content=content)
        case status:
            try:
                http_status = HTTPStatus(status)
            except ValueError:
                http_status = HTTPStatus.INTERNAL_SERVER_ERROR
            return KubexApiError(content=content, status=http_status)
