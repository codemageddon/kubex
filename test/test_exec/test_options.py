from __future__ import annotations

import pytest

from kubex.core.params import ExecOptions


def test_exec_options_command_serializes_as_repeated_command_query_params() -> None:
    options = ExecOptions(command=["sh", "-c", "echo hello"])
    params = options.to_query_params()
    command_pairs = [pair for pair in params if pair[0] == "command"]
    assert command_pairs == [
        ("command", "sh"),
        ("command", "-c"),
        ("command", "echo hello"),
    ]


def test_exec_options_default_boolean_flags_match_kubernetes_defaults() -> None:
    options = ExecOptions(command=["ls"])
    params = dict(options.to_query_params())
    assert params["stdin"] == "false"
    assert params["stdout"] == "true"
    assert params["stderr"] == "true"
    assert params["tty"] == "false"


@pytest.mark.parametrize(
    ("flag", "value", "expected"),
    [
        ("stdin", True, "true"),
        ("stdin", False, "false"),
        ("stdout", True, "true"),
        ("stdout", False, "false"),
        ("stderr", True, "true"),
        ("stderr", False, "false"),
        ("tty", True, "true"),
        ("tty", False, "false"),
    ],
)
def test_exec_options_boolean_flags_serialize_as_lowercase_strings(
    flag: str, value: bool, expected: str
) -> None:
    kwargs: dict[str, bool] = {flag: value}
    options = ExecOptions(command=["ls"], **kwargs)  # type: ignore[arg-type]
    params = dict(options.to_query_params())
    assert params[flag] == expected


def test_exec_options_container_present_when_set() -> None:
    options = ExecOptions(command=["ls"], container="main")
    params = options.to_query_params()
    assert ("container", "main") in params


def test_exec_options_container_omitted_when_none() -> None:
    options = ExecOptions(command=["ls"])
    params = options.to_query_params()
    assert all(pair[0] != "container" for pair in params)


def test_exec_options_returns_list_of_tuples() -> None:
    options = ExecOptions(command=["ls"])
    params = options.to_query_params()
    assert isinstance(params, list)
    assert all(isinstance(pair, tuple) and len(pair) == 2 for pair in params)
    assert all(isinstance(key, str) and isinstance(value, str) for key, value in params)


def test_exec_options_default_command_is_required() -> None:
    with pytest.raises(TypeError):
        ExecOptions()  # type: ignore[call-arg]


def test_exec_options_empty_command_is_rejected() -> None:
    with pytest.raises(ValueError, match="non-empty"):
        ExecOptions(command=[])


@pytest.mark.parametrize("bad", ["sh", "echo hi", b"sh"])
def test_exec_options_rejects_string_or_bytes_command(bad: object) -> None:
    """``str`` satisfies ``Sequence[str]`` (each char is a str) so without an
    explicit guard ``command="sh"`` would explode to ``["s", "h"]``. Validate
    locally instead of letting the API server reject it."""
    with pytest.raises(TypeError, match="sequence of strings"):
        ExecOptions(command=bad)  # type: ignore[arg-type]


@pytest.mark.parametrize("bad", [[1], [b"sh"], ["ok", 2], [None]])
def test_exec_options_rejects_non_string_command_elements(bad: list[object]) -> None:
    """Each element of ``command`` must be a ``str`` — non-strings would
    otherwise serialize via ``__str__`` (or fail at the HTTP layer for
    ``bytes``) and produce a confusing 400 from the API server."""
    with pytest.raises(TypeError, match="must be str"):
        ExecOptions(command=bad)  # type: ignore[arg-type]


def test_exec_options_full_flag_set_serialization() -> None:
    options = ExecOptions(
        command=["bash", "-c", "echo $$"],
        container="sidecar",
        stdin=True,
        stdout=True,
        stderr=False,
        tty=True,
    )
    params = options.to_query_params()
    assert params == [
        ("command", "bash"),
        ("command", "-c"),
        ("command", "echo $$"),
        ("container", "sidecar"),
        ("stdin", "true"),
        ("stdout", "true"),
        ("stderr", "false"),
        ("tty", "true"),
    ]
