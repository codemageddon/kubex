"""Backend-independent helpers shared by the httpx and aiohttp clients."""

from __future__ import annotations

import math
import re
import warnings
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Iterable

# Interval between client-initiated WebSocket pings (both backends). Pings keep
# idle connections alive through load balancers; no pong deadline is enforced
# because a paused consumer stops reading and could never see the pong in time.
WS_PING_INTERVAL_SECONDS = 20.0


def _decode_line(line: bytes | bytearray) -> str:
    if line.endswith(b"\r"):
        line = line[:-1]
    return line.decode("utf-8", errors="replace")


class LineSplitter:
    """Incrementally split a byte stream into text lines.

    Lines end at ``\\n`` only (a trailing ``\\r`` is dropped) — never at other
    Unicode line breaks such as U+0085, which may legitimately occur inside a
    JSON string of a watch event. Splitting happens on raw bytes (``\\n`` can
    not occur inside a multi-byte UTF-8 sequence), and each complete line is
    decoded with ``errors="replace"`` so non-UTF-8 log output never raises.
    There is no line-length cap.
    """

    __slots__ = ("_pending",)

    def __init__(self) -> None:
        self._pending = bytearray()

    def feed(self, chunk: bytes) -> list[str]:
        if b"\n" not in chunk:
            self._pending += chunk
            return []
        parts = chunk.split(b"\n")
        self._pending += parts[0]
        lines = [_decode_line(self._pending)]
        lines.extend(_decode_line(part) for part in parts[1:-1])
        self._pending = bytearray(parts[-1])
        return lines

    def flush(self) -> str | None:
        """Return the final unterminated line, if any."""
        if not self._pending:
            return None
        line = _decode_line(self._pending)
        self._pending = bytearray()
        return line


# RFC 7234 section 5.5: warn-code SP warn-agent SP warn-text [ SP warn-date ],
# with warn-text and warn-date as quoted strings; values are comma-separated.
_WARN_VALUE = re.compile(
    r'[\s,]*(?P<code>\d{3})\s+(?P<agent>[^\s"]+)\s+"(?P<text>(?:[^"\\]|\\.)*)"'
    r'(?:\s+"[^"]*")?\s*(?:,|$)'
)
_QUOTED_PAIR = re.compile(r"\\(.)")


def parse_warning_header(value: str) -> list[str]:
    """Extract the warn-texts from one ``Warning`` header value.

    Commas inside quoted texts are preserved. A value that does not follow the
    RFC 7234 grammar is returned whole, so nothing the server said is lost.
    """
    texts: list[str] = []
    pos = 0
    end = len(value.rstrip(" \t,"))
    while pos < end:
        match = _WARN_VALUE.match(value, pos)
        if match is None:
            return [value.strip()]
        texts.append(_QUOTED_PAIR.sub(r"\1", match.group("text")))
        pos = match.end()
    return texts


def emit_api_warnings(header_values: Iterable[str]) -> None:
    for header_value in header_values:
        for text in parse_warning_header(header_value):
            warnings.warn(f"API Warning: {text}", UserWarning, stacklevel=4)


def parse_retry_after(value: str | None) -> float | None:
    """Parse a ``Retry-After`` header (delta-seconds or HTTP-date) into seconds."""
    if not value:
        return None
    value = value.strip()
    try:
        seconds = float(value)
    except ValueError:
        try:
            when = parsedate_to_datetime(value)
        except (TypeError, ValueError, IndexError):
            return None
        if when.tzinfo is None:
            when = when.replace(tzinfo=timezone.utc)
        seconds = (when - datetime.now(timezone.utc)).total_seconds()
    if not math.isfinite(seconds):
        return None
    return max(0.0, seconds)


def describe_exception(exc: BaseException) -> str:
    return str(exc) or type(exc).__name__
