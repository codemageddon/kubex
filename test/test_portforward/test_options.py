from __future__ import annotations

import pytest

from kubex.core.params import PortForwardOptions


def test_portforward_options_requires_ports() -> None:
    with pytest.raises(TypeError):
        PortForwardOptions()  # type: ignore[call-arg]


def test_portforward_options_rejects_empty_ports() -> None:
    with pytest.raises(ValueError, match="at least one port"):
        PortForwardOptions(ports=[])


def test_portforward_options_rejects_port_zero() -> None:
    with pytest.raises(ValueError, match="out of range"):
        PortForwardOptions(ports=[0])


def test_portforward_options_rejects_port_above_65535() -> None:
    with pytest.raises(ValueError, match="out of range"):
        PortForwardOptions(ports=[65536])


def test_portforward_options_accepts_port_boundary_1() -> None:
    opts = PortForwardOptions(ports=[1])
    assert opts.ports == (1,)


def test_portforward_options_accepts_port_boundary_65535() -> None:
    opts = PortForwardOptions(ports=[65535])
    assert opts.ports == (65535,)


def test_portforward_options_rejects_duplicate_ports() -> None:
    with pytest.raises(ValueError, match="duplicate"):
        PortForwardOptions(ports=[8080, 8080])


def test_portforward_options_preserves_ordering() -> None:
    opts = PortForwardOptions(ports=[9090, 8080, 3000])
    assert opts.ports == (9090, 8080, 3000)


def test_portforward_options_stores_ports_as_tuple() -> None:
    opts = PortForwardOptions(ports=[8080])
    assert isinstance(opts.ports, tuple)


def test_portforward_options_to_query_params_single_port() -> None:
    opts = PortForwardOptions(ports=[8080])
    assert opts.to_query_params() == [("ports", "8080")]


def test_portforward_options_to_query_params_multiple_ports_preserves_order() -> None:
    opts = PortForwardOptions(ports=[8080, 9090, 3000])
    assert opts.to_query_params() == [
        ("ports", "8080"),
        ("ports", "9090"),
        ("ports", "3000"),
    ]


def test_portforward_options_to_query_params_returns_list_of_tuples() -> None:
    opts = PortForwardOptions(ports=[8080, 9090])
    params = opts.to_query_params()
    assert isinstance(params, list)
    assert all(isinstance(p, tuple) and len(p) == 2 for p in params)
    assert all(isinstance(k, str) and isinstance(v, str) for k, v in params)


def test_portforward_options_accepts_sequence_input() -> None:
    opts = PortForwardOptions(ports=(8080, 9090))
    assert opts.ports == (8080, 9090)


@pytest.mark.parametrize(
    "bad_port",
    [-1, 0, 65536, 100000],
)
def test_portforward_options_rejects_invalid_port_values(bad_port: int) -> None:
    with pytest.raises(ValueError, match="out of range"):
        PortForwardOptions(ports=[bad_port])


def test_portforward_options_rejects_more_than_127_ports() -> None:
    # error_channel_for_port_index(127) = 255 = CHANNEL_CLOSE, so 128+ ports collide.
    with pytest.raises(ValueError, match="at most 127 ports"):
        PortForwardOptions(ports=list(range(1, 129)))


def test_portforward_options_accepts_exactly_127_ports() -> None:
    opts = PortForwardOptions(ports=list(range(1, 128)))
    assert len(opts.ports) == 127


def test_portforward_options_rejects_bool_port() -> None:
    with pytest.raises(TypeError, match="port must be int"):
        PortForwardOptions(ports=[True])
