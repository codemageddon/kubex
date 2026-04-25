from __future__ import annotations

import pytest

from kubex.core.exec_channels import (
    CHANNEL_CLOSE,
    CHANNEL_ERROR,
    CHANNEL_RESIZE,
    CHANNEL_STDERR,
    CHANNEL_STDIN,
    CHANNEL_STDOUT,
    DEFAULT_PROTOCOLS,
    V5ChannelProtocol,
    select_protocol,
)


def test_channel_id_constants_match_kubernetes_protocol() -> None:
    assert CHANNEL_STDIN == 0
    assert CHANNEL_STDOUT == 1
    assert CHANNEL_STDERR == 2
    assert CHANNEL_ERROR == 3
    assert CHANNEL_RESIZE == 4
    assert CHANNEL_CLOSE == 255


def test_v5_channel_protocol_subprotocol_string() -> None:
    assert V5ChannelProtocol.subprotocol == "v5.channel.k8s.io"


def test_v5_channel_protocol_instance_subprotocol_accessible() -> None:
    protocol = V5ChannelProtocol()
    assert protocol.subprotocol == "v5.channel.k8s.io"


@pytest.mark.parametrize(
    ("channel", "payload", "expected"),
    [
        (CHANNEL_STDIN, b"hello", b"\x00hello"),
        (CHANNEL_STDOUT, b"out", b"\x01out"),
        (CHANNEL_STDERR, b"err", b"\x02err"),
        (CHANNEL_ERROR, b'{"status":"Success"}', b'\x03{"status":"Success"}'),
        (CHANNEL_RESIZE, b'{"Width":80,"Height":24}', b'\x04{"Width":80,"Height":24}'),
        (CHANNEL_CLOSE, b"\x00", b"\xff\x00"),
        (CHANNEL_STDIN, b"", b"\x00"),
    ],
)
def test_v5_channel_protocol_encode_prepends_channel_byte(
    channel: int, payload: bytes, expected: bytes
) -> None:
    protocol = V5ChannelProtocol()
    assert protocol.encode(channel, payload) == expected


@pytest.mark.parametrize(
    ("frame", "expected_channel", "expected_payload"),
    [
        (b"\x00hello", CHANNEL_STDIN, b"hello"),
        (b"\x01out", CHANNEL_STDOUT, b"out"),
        (b"\x02err", CHANNEL_STDERR, b"err"),
        (b'\x03{"status":"Success"}', CHANNEL_ERROR, b'{"status":"Success"}'),
        (b"\x04{}", CHANNEL_RESIZE, b"{}"),
        (b"\xff\x00", CHANNEL_CLOSE, b"\x00"),
        (b"\x01", CHANNEL_STDOUT, b""),
    ],
)
def test_v5_channel_protocol_decode_returns_channel_and_payload(
    frame: bytes, expected_channel: int, expected_payload: bytes
) -> None:
    protocol = V5ChannelProtocol()
    channel, payload = protocol.decode(frame)
    assert channel == expected_channel
    assert payload == expected_payload


def test_v5_channel_protocol_decode_rejects_empty_frame() -> None:
    protocol = V5ChannelProtocol()
    with pytest.raises(ValueError):
        protocol.decode(b"")


def test_v5_channel_protocol_encode_rejects_out_of_range_channel() -> None:
    protocol = V5ChannelProtocol()
    with pytest.raises(ValueError):
        protocol.encode(-1, b"x")
    with pytest.raises(ValueError):
        protocol.encode(256, b"x")


def test_v5_channel_protocol_encode_decode_roundtrip() -> None:
    protocol = V5ChannelProtocol()
    for channel in (CHANNEL_STDIN, CHANNEL_STDOUT, CHANNEL_ERROR, CHANNEL_CLOSE):
        payload = b"some bytes \x00\xff"
        frame = protocol.encode(channel, payload)
        decoded_channel, decoded_payload = protocol.decode(frame)
        assert decoded_channel == channel
        assert decoded_payload == payload


def test_default_protocols_contains_v5() -> None:
    assert len(DEFAULT_PROTOCOLS) == 1
    assert isinstance(DEFAULT_PROTOCOLS[0], V5ChannelProtocol)


def test_default_protocols_is_tuple() -> None:
    assert isinstance(DEFAULT_PROTOCOLS, tuple)


def test_select_protocol_picks_matching_subprotocol() -> None:
    selected = select_protocol("v5.channel.k8s.io", DEFAULT_PROTOCOLS)
    assert isinstance(selected, V5ChannelProtocol)


def test_select_protocol_picks_first_matching_when_multiple() -> None:
    v5_a = V5ChannelProtocol()
    v5_b = V5ChannelProtocol()
    selected = select_protocol("v5.channel.k8s.io", (v5_a, v5_b))
    assert selected is v5_a


def test_select_protocol_raises_when_none_match() -> None:
    with pytest.raises(ValueError):
        select_protocol("v99.unknown", DEFAULT_PROTOCOLS)


def test_select_protocol_raises_when_subprotocol_none() -> None:
    with pytest.raises(ValueError):
        select_protocol(None, DEFAULT_PROTOCOLS)


def test_select_protocol_raises_with_empty_protocols_tuple() -> None:
    with pytest.raises(ValueError):
        select_protocol("v5.channel.k8s.io", ())


def test_v5_channel_protocol_supports_close() -> None:
    protocol = V5ChannelProtocol()
    assert protocol.supports_close() is True
