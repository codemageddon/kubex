from http import HTTPStatus
from typing import Any, Generic, TypeVar

from kubex.models.status import Status


class KubexException(Exception):
    pass


class KubexClientException(KubexException):
    pass


C = TypeVar("C", bound=str | Status)


class ConfgiurationError(KubexException):
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
        if status is None:
            self.status = HTTPStatus.BAD_REQUEST
        else:
            self.status = status
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


class KubernetesError(KubexApiError[str]):
    status = HTTPStatus.INTERNAL_SERVER_ERROR
