from __future__ import annotations

import json
from collections.abc import Sequence
from enum import Enum
from typing import Any, Literal, Union
from uuid import UUID


class Timeout:
    """Timeout settings for HTTP requests.

    Provides a client-agnostic way to configure timeout settings for the
    underlying HTTP client. Individual fields may be ignored by a given
    implementation if the client library does not support them.

    Args:
        total: Total timeout in seconds for the whole request. Used as the
            default for unset granular fields.
        connect: Timeout in seconds for establishing a connection.
        read: Timeout in seconds for reading the response.
        write: Timeout in seconds for writing the request body.
            Only honored by the httpx backend.
        pool: Timeout in seconds for acquiring a connection from the pool.
            Only honored by the httpx backend.
    """

    __slots__ = ("total", "connect", "read", "write", "pool")

    def __init__(
        self,
        total: float | None = None,
        *,
        connect: float | None = None,
        read: float | None = None,
        write: float | None = None,
        pool: float | None = None,
    ) -> None:
        self.total = total
        self.connect = connect
        self.read = read
        self.write = write
        self.pool = pool

    @classmethod
    def coerce(cls, value: TimeoutTypes) -> Timeout | None:
        """Normalize a ``TimeoutTypes`` value to ``Timeout`` or ``None``."""
        if value is None:
            return None
        if isinstance(value, Timeout):
            return value
        return cls(total=float(value))

    def __repr__(self) -> str:
        return (
            f"Timeout(total={self.total}, connect={self.connect}, "
            f"read={self.read}, write={self.write}, pool={self.pool})"
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Timeout):
            return NotImplemented
        return (
            self.total == other.total
            and self.connect == other.connect
            and self.read == other.read
            and self.write == other.write
            and self.pool == other.pool
        )

    def __hash__(self) -> int:
        return hash((self.total, self.connect, self.read, self.write, self.pool))


TimeoutTypes = Union[Timeout, float, int, None]


class VersionMatch(str, Enum):
    EXACT = "Exact"
    NOT_EXACT = "NotOlderThan"


class PropagationPolicy(str, Enum):
    BACKGROUND = "Background"
    FOREGROUND = "Foreground"
    ORPHAN = "Orphan"


class FieldValidation(str, Enum):
    IGNORE = "Ignore"
    STRICT = "Strict"
    WARN = "Warn"


class DryRun(str, Enum):
    ALL = "All"


PropagationPolicyTypes = (
    PropagationPolicy | Literal["Background", "Foreground", "Orphan"] | None
)
DryRunTypes = DryRun | bool | Literal["All"] | None
UidTypes = UUID | str | None
ResourceVersionTypes = str | None
NamespaceTypes = str | None


class Precondition:
    def __init__(
        self,
        resource_version: ResourceVersionTypes = None,
        uid: UidTypes = None,
    ) -> None:
        self.resource_version = resource_version
        self.uid = uid


class ListOptions:
    def __init__(
        self,
        label_selector: str | None = None,
        field_selector: str | None = None,
        timeout: int | None = None,
        limit: int | None = None,
        continue_token: str | None = None,
        version_match: VersionMatch | None = None,
        resource_version: ResourceVersionTypes = None,
    ) -> None:
        self.label_selector = label_selector
        self.field_selector = field_selector
        self.timeout = timeout
        self.limit = limit
        self.continue_token = continue_token
        self.version_match = version_match
        self.resource_version = resource_version

    @classmethod
    def default(cls) -> ListOptions:
        return cls()

    def as_query_params(self) -> dict[str, str] | None:
        query_params = {}
        if self.label_selector is not None:
            query_params["labelSelector"] = self.label_selector
        if self.field_selector is not None:
            query_params["fieldSelector"] = self.field_selector
        if self.timeout is not None:
            query_params["timeoutSeconds"] = str(self.timeout)
        if self.limit is not None:
            query_params["limit"] = str(self.limit)
        if self.continue_token is not None:
            query_params["continue"] = self.continue_token
        if self.version_match is not None:
            query_params["resourceVersionMatch"] = self.version_match.value
        if self.resource_version is not None:
            query_params["resourceVersion"] = self.resource_version
        return query_params or None


class WatchOptions:
    def __init__(
        self,
        label_selector: str | None = None,
        field_selector: str | None = None,
        allow_bookmarks: bool | None = None,
        send_initial_events: bool | None = None,
        timeout_seconds: int | None = None,
    ) -> None:
        self.label_selector = label_selector
        self.field_selector = field_selector
        self.allow_bookmarks = allow_bookmarks
        self.send_initial_events = send_initial_events
        self.timeout_seconds = timeout_seconds

    @classmethod
    def default(cls) -> WatchOptions:
        return cls()

    def as_query_params(self) -> dict[str, str]:
        query_params = {"watch": "true"}
        if self.label_selector is not None:
            query_params["labelSelector"] = self.label_selector
        if self.field_selector is not None:
            query_params["fieldSelector"] = self.field_selector
        if self.allow_bookmarks is not None:
            query_params["allowBookmarks"] = "true" if self.allow_bookmarks else "false"
        if self.send_initial_events is not None:
            query_params["sendInitialEvents"] = (
                "true" if self.send_initial_events else "false"
            )
        if self.timeout_seconds is not None:
            query_params["timeoutSeconds"] = str(self.timeout_seconds)
        return query_params


class GetOptions:
    def __init__(
        self,
        resource_version: ResourceVersionTypes = None,
    ) -> None:
        self.resource_version = resource_version

    @classmethod
    def default(cls) -> GetOptions:
        return cls()

    def as_query_params(self) -> dict[str, str] | None:
        if self.resource_version is None:
            return None
        return {"resourceVersion": self.resource_version}


def convert_dry_run(dry_run: DryRunTypes) -> DryRun | None:
    if dry_run is None:
        return None
    if isinstance(dry_run, DryRun):
        return dry_run
    elif isinstance(dry_run, str):
        return DryRun(dry_run)
    return DryRun.ALL if dry_run else None


class PostOptions:
    def __init__(
        self,
        dry_run: DryRunTypes = None,
        field_manager: str | None = None,
    ) -> None:
        self.dry_run = dry_run
        self.field_manager = field_manager

    @classmethod
    def default(cls) -> PostOptions:
        return cls()

    def as_query_params(self) -> dict[str, str] | None:
        query_params = {}
        dry_run = convert_dry_run(self.dry_run)
        if dry_run is not None:
            query_params["dryRun"] = dry_run.value
        if self.field_manager is not None:
            query_params["fieldManager"] = self.field_manager
        return query_params or None


class PatchOptions:
    def __init__(
        self,
        dry_run: DryRunTypes = None,
        field_manager: str | None = None,
        force: bool | None = None,
        field_validation: FieldValidation | None = None,
    ) -> None:
        self.dry_run = dry_run
        self.field_manager = field_manager
        self.force = force
        self.field_validation = field_validation

    @classmethod
    def default(cls) -> PatchOptions:
        return cls()

    def as_query_params(self) -> dict[str, str] | None:
        query_params = {}
        dry_run = convert_dry_run(self.dry_run)
        if dry_run is not None:
            query_params["dryRun"] = dry_run.value
        if self.field_manager is not None:
            query_params["fieldManager"] = self.field_manager
        if self.force is not None:
            query_params["force"] = "true" if self.force else "false"
        if self.field_validation is not None:
            query_params["fieldValidation"] = self.field_validation.value
        return query_params or None


class DeleteOptions:
    def __init__(
        self,
        dry_run: DryRunTypes = None,
        grace_period_seconds: int | None = None,
        propagation_policy: PropagationPolicyTypes = None,
        preconditions: Precondition | None = None,
    ) -> None:
        self.dry_run = dry_run
        self.grace_period_seconds = grace_period_seconds
        self.propagation_policy = propagation_policy
        self.preconditions = preconditions

    @classmethod
    def default(cls) -> DeleteOptions:
        return cls()

    def as_request_body(self) -> str | None:
        body: dict[str, Any] = {}
        dry_run = convert_dry_run(self.dry_run)
        if dry_run is not None:
            body["dryRun"] = dry_run.value
        if self.grace_period_seconds is not None:
            body["gracePeriodSeconds"] = self.grace_period_seconds
        if self.propagation_policy is not None:
            if isinstance(self.propagation_policy, PropagationPolicy):
                body["propagationPolicy"] = self.propagation_policy.value
            else:
                body["propagationPolicy"] = self.propagation_policy
        if self.preconditions is not None:
            preconditions_dict: dict[str, str] = {}
            if self.preconditions.resource_version is not None:
                preconditions_dict["resourceVersion"] = (
                    self.preconditions.resource_version
                )
            if self.preconditions.uid is not None:
                preconditions_dict["uid"] = str(self.preconditions.uid)
            if preconditions_dict:
                body["preconditions"] = preconditions_dict
        if body:
            return json.dumps(body)
        return None


class ExecOptions:
    """Options for the Pod ``exec`` subresource.

    Mirrors the ``v1.PodExecOptions`` Kubernetes API. ``command`` is required
    and must be a non-empty sequence of strings — each element serializes as a
    separate ``command=`` query parameter. Boolean flags serialize as the
    lowercase strings ``"true"`` / ``"false"`` to match what the Kubernetes API
    server expects.
    """

    __slots__ = ("command", "container", "stdin", "stdout", "stderr", "tty")

    def __init__(
        self,
        *,
        command: Sequence[str],
        container: str | None = None,
        stdin: bool = False,
        stdout: bool = True,
        stderr: bool = True,
        tty: bool = False,
    ) -> None:
        # ``str`` satisfies ``Sequence[str]`` (each character is itself a
        # ``str``), so ``list("sh")`` would silently produce ``["s", "h"]``
        # and emit a broken request. Reject it explicitly so callers see a
        # clear local validation error instead of a confusing 400 from the
        # API server.
        if isinstance(command, (str, bytes)):
            raise TypeError(
                "command must be a sequence of strings, not a single "
                f"{type(command).__name__}; pass e.g. ['sh', '-c', 'echo hi']"
            )
        self.command = list(command)
        if not self.command:
            raise ValueError("command must be a non-empty sequence of strings")
        # Each element must be a ``str`` — non-strings would otherwise
        # serialize via ``__str__`` (or fail at the HTTP layer for ``bytes``)
        # and produce a confusing 400 from the API server. Validate here so
        # callers see a clear local error instead.
        for index, element in enumerate(self.command):
            if not isinstance(element, str):
                raise TypeError(
                    f"command[{index}] must be str, got {type(element).__name__}"
                )
        self.container = container
        self.stdin = stdin
        self.stdout = stdout
        self.stderr = stderr
        self.tty = tty

    def to_query_params(self) -> list[tuple[str, str]]:
        params: list[tuple[str, str]] = [("command", c) for c in self.command]
        if self.container is not None:
            params.append(("container", self.container))
        params.append(("stdin", "true" if self.stdin else "false"))
        params.append(("stdout", "true" if self.stdout else "false"))
        params.append(("stderr", "true" if self.stderr else "false"))
        params.append(("tty", "true" if self.tty else "false"))
        return params


class AttachOptions:
    """Options for the Pod ``attach`` subresource. Mirrors ``v1.PodAttachOptions``."""

    __slots__ = ("container", "stdin", "stdout", "stderr", "tty")

    def __init__(
        self,
        *,
        container: str | None = None,
        stdin: bool = False,
        stdout: bool = True,
        stderr: bool = True,
        tty: bool = False,
    ) -> None:
        self.container = container
        self.stdin = stdin
        self.stdout = stdout
        self.stderr = stderr
        self.tty = tty

    def to_query_params(self) -> list[tuple[str, str]]:
        params: list[tuple[str, str]] = []
        if self.container is not None:
            params.append(("container", self.container))
        params.append(("stdin", "true" if self.stdin else "false"))
        params.append(("stdout", "true" if self.stdout else "false"))
        params.append(("stderr", "true" if self.stderr else "false"))
        params.append(("tty", "true" if self.tty else "false"))
        return params


class PortForwardOptions:
    """Options for the Pod ``portforward`` subresource.

    Validates that ports are unique, non-empty, and within 1..65535.
    ``to_query_params()`` returns repeated ``("ports", "<n>")`` pairs in input order.
    """

    __slots__ = ("ports",)

    def __init__(self, *, ports: Sequence[int]) -> None:
        ports_t = tuple(ports)
        if not ports_t:
            raise ValueError("portforward requires at least one port")
        if len(set(ports_t)) != len(ports_t):
            raise ValueError("duplicate ports are not allowed")
        # Channel IDs are a single byte (0..255).  Two channels per port
        # (data=2i, error=2i+1) means index 127 maps to error channel
        # 2*127+1 = 255, which collides with the v5 CHANNEL_CLOSE sentinel.
        # The kubelet portforward currently negotiates v4 only (no
        # CHANNEL_CLOSE sentinel), but we cap at 127 to stay forward-compatible
        # with v5 and to keep error-channel ids inside [0, 254].
        if len(ports_t) > 127:
            raise ValueError(
                f"portforward supports at most 127 ports, got {len(ports_t)}"
            )
        for p in ports_t:
            if isinstance(p, bool) or not isinstance(p, int):
                raise TypeError(f"port must be int, got {type(p).__name__}")
            if not 1 <= p <= 65535:
                raise ValueError(f"port {p} out of range 1..65535")
        self.ports = ports_t

    def to_query_params(self) -> list[tuple[str, str]]:
        return [("ports", str(p)) for p in self.ports]


class LogOptions:
    def __init__(
        self,
        container: str | None = None,
        limit_bytes: int | None = None,
        pretty: bool | None = None,
        previous: bool | None = None,
        since_seconds: int | None = None,
        tail_lines: int | None = None,
        timestamps: bool | None = None,
    ) -> None:
        self.container = container
        self.limit_bytes = limit_bytes
        self.pretty = pretty
        self.previous = previous
        self.since_seconds = since_seconds
        self.tail_lines = tail_lines
        self.timestamps = timestamps

    @classmethod
    def default(cls) -> LogOptions:
        return cls()

    def as_query_params(self) -> dict[str, str] | None:
        result: dict[str, str] = {}
        if self.container is not None:
            result["container"] = self.container
        if self.limit_bytes is not None:
            result["limitBytes"] = str(self.limit_bytes)
        if self.pretty is not None:
            result["pretty"] = "true" if self.pretty else "false"
        if self.previous is not None:
            result["previous"] = "true" if self.previous else "false"
        if self.since_seconds is not None:
            result["sinceSeconds"] = str(self.since_seconds)
        if self.tail_lines is not None:
            result["tailLines"] = str(self.tail_lines)
        if self.timestamps is not None:
            result["timestamps"] = "true" if self.timestamps else "false"
        return result or None
