from __future__ import annotations

import pytest

from kubex.core.exceptions import KubexClientException
from kubex.core.exec_channels import (
    data_channel_for_port_index,
    error_channel_for_port_index,
    port_prefix_decode,
    port_prefix_encode,
)


@pytest.mark.parametrize(
    "index,expected_data,expected_error",
    [
        (0, 0, 1),
        (1, 2, 3),
        (2, 4, 5),
        (5, 10, 11),
    ],
)
def test_channel_ids_for_port_index(
    index: int, expected_data: int, expected_error: int
) -> None:
    assert data_channel_for_port_index(index) == expected_data
    assert error_channel_for_port_index(index) == expected_error


def test_port_prefix_encode_8080() -> None:
    assert port_prefix_encode(8080) == b"\x90\x1f"


def test_port_prefix_encode_80() -> None:
    assert port_prefix_encode(80) == b"\x50\x00"


def test_port_prefix_encode_max() -> None:
    assert port_prefix_encode(65535) == b"\xff\xff"


def test_port_prefix_encode_min() -> None:
    assert port_prefix_encode(1) == b"\x01\x00"


def test_port_prefix_decode_8080() -> None:
    assert port_prefix_decode(b"\x90\x1f") == 8080


def test_port_prefix_decode_80() -> None:
    assert port_prefix_decode(b"\x50\x00") == 80


def test_port_prefix_decode_with_extra_bytes() -> None:
    assert port_prefix_decode(b"\x90\x1fextra") == 8080


def test_port_prefix_decode_too_short_raises() -> None:
    with pytest.raises(KubexClientException):
        port_prefix_decode(b"\x90")


def test_port_prefix_decode_empty_raises() -> None:
    with pytest.raises(KubexClientException):
        port_prefix_decode(b"")


def test_roundtrip() -> None:
    for port in (1, 80, 443, 8080, 9090, 65535):
        assert port_prefix_decode(port_prefix_encode(port)) == port
