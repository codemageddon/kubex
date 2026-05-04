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
                proxy="http://proxy.corp.example.com:8080",
                keep_alive_timeout=60.0,
                pool_size=50,
                ws_max_message_size=8 * 1024 * 1024,
            ),
        )

    **Backend asymmetries**

    Some fields are silently ignored on certain backends (a :class:`UserWarning`
    is emitted at client construction time):

    - ``buffer_size``: httpx has no equivalent buffer-size knob; the value is
      ignored and a warning is raised.
    - ``pool_size_per_host``: httpx has no per-host pool limit; the value is
      ignored and a warning is raised.
    - ``keep_alive_timeout=None``: aiohttp has no "unlimited keep-alive" mode.
      The value is ignored (aiohttp falls back to its own default) and a warning
      is raised.
    - ``proxy=dict``: aiohttp supports only a single session-level proxy URL.
      The entry whose key matches the API server's URL scheme is used; all other
      entries are dropped with a warning. httpx applies all dict entries via
      ``mounts=``.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

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

    proxy: str | dict[str, str] | None = None
    """Outbound HTTP proxy for all requests.

    Accepted values:

    - ``None`` (default) — no proxy.
    - ``str`` — a single proxy URL applied to every request, e.g.
      ``"http://proxy.example.com:8080"`` or
      ``"http://user:pass@proxy.example.com:8080"`` for basic auth.
    - ``dict[str, str]`` — per-scheme map with ``"http"`` and/or ``"https"``
      keys, e.g. ``{"https": "http://proxy.example.com:8080"}``. Only
      ``"http"`` and ``"https"`` scheme keys are accepted.

    **Backend asymmetry**: httpx routes all dict entries via ``mounts=``;
    aiohttp supports only a single session-level proxy URL, so only the entry
    matching the API server's URL scheme is used (others are dropped with a
    warning).
    """

    keep_alive: bool = True
    """Whether to reuse idle connections (connection keep-alive).

    Set to ``False`` to close each connection immediately after use. This maps
    to ``Limits(max_keepalive_connections=0)`` on httpx and
    ``TCPConnector(force_close=True)`` on aiohttp.
    """

    keep_alive_timeout: float | None | EllipsisType = Field(default_factory=lambda: ...)
    """Idle-connection lifetime in seconds.

    Accepted values:

    - ``...`` (default) — use the HTTP library's own default (httpx: 5 s;
      aiohttp: 15 s).
    - ``None`` — keep idle connections indefinitely. On httpx this passes
      ``keepalive_expiry=None``; on aiohttp this is not supported (aiohttp
      has no "unlimited" mode) and a :class:`UserWarning` is emitted.
    - ``float >= 0`` — explicit lifetime in seconds.
    """

    buffer_size: int | None | EllipsisType = Field(default_factory=lambda: ...)
    """HTTP-response read buffer size in bytes.

    Accepted values:

    - ``...`` (default) — kubex default of ``2**21`` bytes (preserves current
      aiohttp behavior).
    - ``None`` — use the HTTP library's own default (aiohttp default: ``2**16``
      bytes).
    - ``int > 0`` — explicit buffer size in bytes.

    **Backend asymmetry**: httpx has no equivalent buffer-size knob. This field
    is ignored on httpx and a :class:`UserWarning` is emitted if it is not
    ``...``.
    """

    ws_max_message_size: int | None | EllipsisType = Field(default_factory=lambda: ...)
    """Maximum WebSocket message size in bytes for ``exec``/``attach``/``portforward``.

    Accepted values:

    - ``...`` (default) — kubex default of ``2**21`` bytes (preserves current
      behavior on both backends).
    - ``None`` — no cap on aiohttp (passes ``0`` to ``max_msg_size``). On httpx,
      ``None`` is not supported; falls back to httpx-ws default (65536 bytes) and a
      :class:`UserWarning` is emitted.
    - ``int > 0`` — explicit cap in bytes.
    """

    pool_size: int | None | EllipsisType = Field(default_factory=lambda: ...)
    """Total connection pool size (all hosts combined).

    Accepted values:

    - ``...`` (default) — use the HTTP library's own default (httpx: 100;
      aiohttp: 100).
    - ``None`` — unlimited (passes ``None`` to httpx, ``0`` to aiohttp).
    - ``int > 0`` — explicit connection limit.
    """

    pool_size_per_host: int | None | EllipsisType = Field(default_factory=lambda: ...)
    """Per-host connection pool size.

    Accepted values:

    - ``...`` (default) — use the HTTP library's own default (aiohttp: 0,
      meaning no per-host limit).
    - ``None`` — unlimited (passes ``0`` to aiohttp).
    - ``int > 0`` — explicit per-host connection limit.

    **Backend asymmetry**: httpx has no per-host pool limit. This field is
    ignored on httpx and a :class:`UserWarning` is emitted if it is not ``...``.
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

    @field_validator("proxy", mode="before")
    @classmethod
    def _normalize_proxy(cls, value: object) -> object:
        if value is None:
            return value
        if isinstance(value, str):
            if not value:
                raise ValueError("proxy str must not be empty")
            return value
        if isinstance(value, dict):
            if not value:
                raise ValueError("proxy dict must not be empty")
            allowed_schemes = {"http", "https"}
            for k, v in value.items():
                if not isinstance(k, str):
                    raise ValueError(
                        f"proxy dict keys must be strings, got {type(k).__name__!r}"
                    )
                if not isinstance(v, str):
                    raise ValueError(
                        f"proxy dict values must be strings, got {type(v).__name__!r}"
                    )
                if not v:
                    raise ValueError(
                        f"proxy dict value for scheme {k!r} must not be empty"
                    )
                if k not in allowed_schemes:
                    raise ValueError(
                        f"proxy dict key {k!r} is not a recognised scheme; "
                        f"allowed keys are {sorted(allowed_schemes)!r}"
                    )
            return value
        raise ValueError(
            f"proxy must be None, a str URL, or a dict[str, str]; got {type(value).__name__!r}"
        )

    @field_validator("keep_alive_timeout", mode="before")
    @classmethod
    def _normalize_keep_alive_timeout(cls, value: object) -> object:
        if value is Ellipsis or value is None:
            return value
        if isinstance(value, bool):
            raise ValueError(
                "keep_alive_timeout must not be a bool; pass a float (seconds), None, or ..."
            )
        if isinstance(value, (int, float)):
            f = float(value)
            if f < 0:
                raise ValueError(f"keep_alive_timeout must be >= 0, got {f}")
            return f
        raise ValueError(
            f"keep_alive_timeout must be a float, None, or ...; got {type(value).__name__!r}"
        )

    @field_validator("buffer_size", "ws_max_message_size", "pool_size", mode="before")
    @classmethod
    def _normalize_positive_int_or_sentinel(cls, value: object) -> object:
        if value is Ellipsis or value is None:
            return value
        if isinstance(value, bool):
            raise ValueError("value must not be a bool; pass an int > 0, None, or ...")
        if not isinstance(value, int):
            raise ValueError(
                f"value must be an int > 0, None, or ...; got {type(value).__name__!r}"
            )
        if value <= 0:
            raise ValueError(f"value must be > 0, got {value}")
        return value

    @field_validator("pool_size_per_host", mode="before")
    @classmethod
    def _normalize_pool_size_per_host(cls, value: object) -> object:
        if value is Ellipsis or value is None:
            return value
        if isinstance(value, bool):
            raise ValueError(
                "pool_size_per_host must not be a bool; pass an int > 0, None, or ..."
            )
        if not isinstance(value, int):
            raise ValueError(
                f"pool_size_per_host must be an int > 0, None, or ...; "
                f"got {type(value).__name__!r}"
            )
        if value <= 0:
            raise ValueError(
                f"pool_size_per_host must be > 0 (use None for unlimited), got {value}"
            )
        return value


def resolve_ws_max_message_size(ws_max_message_size: int | None | EllipsisType) -> int:
    """Resolve ``ws_max_message_size`` to a concrete integer for HTTP backends.

    - ``...`` → ``2**21`` (kubex default; preserves pre-option behavior on both backends)
    - ``None`` → ``0`` (aiohttp treats 0 as "no cap"; httpx does not pass this at all)
    - ``int``  → that int
    """
    if isinstance(ws_max_message_size, EllipsisType):
        return 2**21
    if ws_max_message_size is None:
        return 0
    return ws_max_message_size
