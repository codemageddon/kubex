from __future__ import annotations

from datetime import datetime, timedelta, timezone
from email.utils import format_datetime

import pytest

from kubex.client._common import (
    LineSplitter,
    parse_retry_after,
    parse_warning_header,
)


def _split(chunks: list[bytes]) -> list[str]:
    splitter = LineSplitter()
    lines = [line for chunk in chunks for line in splitter.feed(chunk)]
    if (tail := splitter.flush()) is not None:
        lines.append(tail)
    return lines


@pytest.mark.parametrize(
    ("chunks", "expected"),
    [
        pytest.param([b"a\nb\n"], ["a", "b"], id="plain"),
        pytest.param([b"a\r\nb\r\n"], ["a", "b"], id="crlf"),
        pytest.param([b"a\r", b"\nb"], ["a", "b"], id="crlf-split"),
        pytest.param([b"a\rb\n"], ["a\rb"], id="lone-cr-kept"),
        pytest.param([b"a\n\nb\n"], ["a", "", "b"], id="blank-line"),
        pytest.param([b"x\xc2\x85y\n"], ["x\x85y"], id="nel-not-a-break"),
        pytest.param([b"\xe2\x80", b"\xa8\n"], [" "], id="split-multibyte"),
        pytest.param([b"\xff\n"], ["�"], id="invalid-utf8"),
        pytest.param([b"tail"], ["tail"], id="unterminated"),
        pytest.param([b"", b"a", b"", b"b\n"], ["ab"], id="empty-chunks"),
        pytest.param([], [], id="empty"),
    ],
)
def test_line_splitter(chunks: list[bytes], expected: list[str]) -> None:
    assert _split(chunks) == expected


def test_line_splitter_handles_many_small_chunks_of_one_long_line() -> None:
    splitter = LineSplitter()
    for _ in range(10_000):
        assert splitter.feed(b"x" * 512) == []
    assert splitter.feed(b"\n") == ["x" * 5_120_000]


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        pytest.param(
            '299 - "deprecated in v1.21+, unavailable in v1.25+"',
            ["deprecated in v1.21+, unavailable in v1.25+"],
            id="comma-in-text",
        ),
        pytest.param(
            '299 - "one", 299 host:443 "two, too"',
            ["one", "two, too"],
            id="multiple",
        ),
        pytest.param(
            '299 - "escaped \\"quote\\" and \\\\ backslash"',
            ['escaped "quote" and \\ backslash'],
            id="quoted-pair",
        ),
        pytest.param(
            '110 - "stale" "Sat, 25 Aug 2012 23:34:45 GMT", 299 - "x"',
            ["stale", "x"],
            id="with-date",
        ),
        pytest.param("299 - deprecated", ["299 - deprecated"], id="unquoted-raw"),
        pytest.param("garbage, more", ["garbage, more"], id="garbage-raw"),
        pytest.param("", [], id="empty"),
    ],
)
def test_parse_warning_header(value: str, expected: list[str]) -> None:
    assert parse_warning_header(value) == expected


def test_parse_retry_after_seconds_and_date() -> None:
    assert parse_retry_after("7") == 7.0
    assert parse_retry_after(" 0 ") == 0.0
    assert parse_retry_after("-3") == 0.0
    assert parse_retry_after(None) is None
    assert parse_retry_after("soon") is None
    assert parse_retry_after("nan") is None
    future = datetime.now(timezone.utc) + timedelta(seconds=60)
    parsed = parse_retry_after(format_datetime(future, usegmt=True))
    assert parsed is not None and 55 <= parsed <= 61
    past = datetime.now(timezone.utc) - timedelta(seconds=60)
    assert parse_retry_after(format_datetime(past, usegmt=True)) == 0.0
