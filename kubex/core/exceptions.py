from http import HTTPStatus
from typing import Any, Generic, TypeVar

from kubex_core.models.status import Status


class KubexException(Exception):
    pass


class KubexClientException(KubexException):
    pass


class KubexConnectionError(KubexClientException):
    """The API server could not be reached, or the connection broke mid-response."""


class KubexTimeoutError(KubexClientException, TimeoutError):
    """A request exceeded its client-side timeout.

    Also a ``TimeoutError``, so ``except TimeoutError`` keeps working.
    """


C = TypeVar("C", bound=str | Status)


class ConfigurationError(KubexException):
    pass


class ConfigurationValueError(ConfigurationError, ValueError):
    """A configuration failure that used to raise ``ValueError``.

    Also a ``ValueError``, so ``except ValueError`` keeps working.
    """


_MAX_MESSAGE_BODY_CHARS = 500


def _describe_error(status: HTTPStatus, content: str | Status) -> str:
    head = f"{status.value} {status.phrase}"
    if isinstance(content, Status):
        message = (content.message or "").strip()
        reason = (content.reason or "").strip()
        if message and reason:
            return f"{head}: {message} (reason: {reason})"
        if message or reason:
            return f"{head}: {message or reason}"
        return head
    body = content.strip()
    if not body:
        return head
    if len(body) > _MAX_MESSAGE_BODY_CHARS:
        body = body[:_MAX_MESSAGE_BODY_CHARS] + "..."
    return f"{head}: {body}"


class KubexApiError(Generic[C], KubexClientException):
    status: HTTPStatus
    content: C
    retry_after: float | None = None
    """Seconds to wait before retrying, from the ``Retry-After`` response header
    (or the Status ``details.retryAfterSeconds``) when the server sent one —
    typically on ``429 Too Many Requests`` and ``503 Service Unavailable``."""

    def __init__(
        self,
        content: C,
        *args: Any,
        status: HTTPStatus | None = None,
        retry_after: float | None = None,
    ) -> None:
        if status is not None:
            self.status = status
        elif not hasattr(type(self), "status"):
            self.status = HTTPStatus.BAD_REQUEST
        self.content = content
        if retry_after is not None:
            self.retry_after = retry_after
        super().__init__(*(args or (_describe_error(self.status, content),)))


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


class TooManyRequests(KubexApiError[C]):
    status = HTTPStatus.TOO_MANY_REQUESTS


class KubernetesError(KubexApiError[C]):
    status = HTTPStatus.INTERNAL_SERVER_ERROR


def build_exception(
    status_code: int,
    content: C,
    *,
    retry_after: float | None = None,
) -> KubexApiError[C]:
    if retry_after is None and isinstance(content, Status) and content.details:
        if (seconds := content.details.retry_after_seconds) is not None:
            retry_after = float(seconds)
    match status_code:
        case HTTPStatus.BAD_REQUEST:
            return BadRequest(content=content, retry_after=retry_after)
        case HTTPStatus.UNAUTHORIZED:
            return Unauthorized(content=content, retry_after=retry_after)
        case HTTPStatus.FORBIDDEN:
            return Forbidden(content=content, retry_after=retry_after)
        case HTTPStatus.NOT_FOUND:
            return NotFound(content=content, retry_after=retry_after)
        case HTTPStatus.METHOD_NOT_ALLOWED:
            return MethodNotAllowed(content=content, retry_after=retry_after)
        case HTTPStatus.CONFLICT:
            return Conflict(content=content, retry_after=retry_after)
        case HTTPStatus.GONE:
            return Gone(content=content, retry_after=retry_after)
        case HTTPStatus.UNPROCESSABLE_ENTITY:
            return UnprocessableEntity(content=content, retry_after=retry_after)
        case HTTPStatus.TOO_MANY_REQUESTS:
            return TooManyRequests(content=content, retry_after=retry_after)
        case HTTPStatus.INTERNAL_SERVER_ERROR:
            return KubernetesError(content=content, retry_after=retry_after)
        case status:
            try:
                http_status = HTTPStatus(status)
            except ValueError:
                http_status = HTTPStatus.INTERNAL_SERVER_ERROR
            return KubexApiError(
                content=content, status=http_status, retry_after=retry_after
            )
