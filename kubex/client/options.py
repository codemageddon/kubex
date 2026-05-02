from __future__ import annotations

from types import EllipsisType

from pydantic import BaseModel, ConfigDict, Field, field_validator

from kubex.core.params import Timeout, TimeoutTypes


class ClientOptions(BaseModel):
    """Operational options for a kubex HTTP client.

    These settings are per-process choices about how the HTTP client should
    behave at request time. They do not come from kubeconfig or the in-cluster
    environment — use :class:`~kubex.configuration.ClientConfiguration` for
    those.

    Example::

        from kubex.client import ClientOptions, create_client
        from kubex.core.params import Timeout

        client = await create_client(
            configuration=...,
            options=ClientOptions(
                log_api_warnings=False,
                timeout=Timeout(total=30.0),
            ),
        )
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    log_api_warnings: bool = True
    """Emit Python :mod:`warnings` for any ``Warning`` HTTP headers returned by
    the API server.

    The Kubernetes API server emits ``Warning:`` response headers to signal
    deprecated API usage (e.g. calling a removed API version). When this is
    ``True`` (the default), kubex converts each header value into a
    :class:`UserWarning` via :func:`warnings.warn`. Set to ``False``
    to silence those warnings.
    """

    timeout: TimeoutTypes | EllipsisType = Field(default_factory=lambda: ...)
    """Default HTTP timeout for every request made by this client.

    Accepted values:

    - ``...`` (default) — use the HTTP library's own default timeout.
    - ``None`` — disable timeouts entirely.
    - ``int`` or ``float`` — treat the value as a ``total`` timeout in seconds;
      coerced to :class:`~kubex.core.params.Timeout` automatically.
    - :class:`~kubex.core.params.Timeout` — used as-is for fine-grained
      per-phase control.

    Individual calls can override this via the ``request_timeout=`` parameter.
    """

    @field_validator("timeout", mode="before")
    @classmethod
    def _normalize_timeout(cls, value: object) -> object:
        if value is Ellipsis or value is None or isinstance(value, Timeout):
            return value
        if isinstance(value, bool):
            raise ValueError(
                "timeout must not be a bool; pass a number (seconds), Timeout, None, or ..."
            )
        try:
            return Timeout.coerce(value)  # type: ignore[arg-type]
        except TypeError as e:
            raise ValueError(str(e)) from e
