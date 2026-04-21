from kubex.configuration import ClientConfiguration
from kubex.core.params import Timeout


def _base_config(**kwargs: object) -> ClientConfiguration:
    return ClientConfiguration(
        url="https://example.invalid",
        insecure_skip_tls_verify=True,
        **kwargs,  # type: ignore[arg-type]
    )


def test_default_timeout_is_ellipsis() -> None:
    config = _base_config()
    assert config.timeout is Ellipsis


def test_explicit_none_preserved() -> None:
    config = _base_config(timeout=None)
    assert config.timeout is None


def test_int_normalized_to_timeout() -> None:
    config = _base_config(timeout=3)
    assert config.timeout == Timeout(total=3.0)


def test_float_normalized_to_timeout() -> None:
    config = _base_config(timeout=2.5)
    assert config.timeout == Timeout(total=2.5)


def test_timeout_instance_passthrough() -> None:
    t = Timeout(connect=1, read=2)
    config = _base_config(timeout=t)
    assert config.timeout is t
