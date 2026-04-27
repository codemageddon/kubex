from __future__ import annotations

import pytest

from kubex.core.params import AttachOptions


def test_attach_options_default_construction() -> None:
    options = AttachOptions()
    assert options.container is None
    assert options.stdin is False
    assert options.stdout is True
    assert options.stderr is True
    assert options.tty is False


def test_attach_options_to_query_params_always_emits_all_flags() -> None:
    options = AttachOptions()
    params = options.to_query_params()
    keys = [k for k, _ in params]
    assert "stdin" in keys
    assert "stdout" in keys
    assert "stderr" in keys
    assert "tty" in keys


def test_attach_options_boolean_flags_serialize_as_lowercase_strings() -> None:
    options = AttachOptions(stdin=True, stdout=False, stderr=False, tty=True)
    params = dict(options.to_query_params())
    assert params["stdin"] == "true"
    assert params["stdout"] == "false"
    assert params["stderr"] == "false"
    assert params["tty"] == "true"


def test_attach_options_default_flags_serialize_correctly() -> None:
    options = AttachOptions()
    params = dict(options.to_query_params())
    assert params["stdin"] == "false"
    assert params["stdout"] == "true"
    assert params["stderr"] == "true"
    assert params["tty"] == "false"


def test_attach_options_container_included_when_set() -> None:
    options = AttachOptions(container="main")
    params = options.to_query_params()
    assert ("container", "main") in params


def test_attach_options_container_omitted_when_none() -> None:
    options = AttachOptions()
    params = options.to_query_params()
    assert all(k != "container" for k, _ in params)


def test_attach_options_no_command_parameter() -> None:
    with pytest.raises(TypeError):
        AttachOptions(command=["sh"])  # type: ignore[call-arg]


def test_attach_options_all_flags_false_accepted() -> None:
    options = AttachOptions(stdin=False, stdout=False, stderr=False)
    params = dict(options.to_query_params())
    assert params["stdin"] == "false"
    assert params["stdout"] == "false"
    assert params["stderr"] == "false"


def test_attach_options_returns_list_of_tuples() -> None:
    options = AttachOptions()
    params = options.to_query_params()
    assert isinstance(params, list)
    assert all(isinstance(pair, tuple) and len(pair) == 2 for pair in params)
    assert all(isinstance(k, str) and isinstance(v, str) for k, v in params)


def test_attach_options_full_serialization_with_container() -> None:
    options = AttachOptions(
        container="sidecar", stdin=True, stdout=True, stderr=False, tty=True
    )
    params = options.to_query_params()
    assert params == [
        ("container", "sidecar"),
        ("stdin", "true"),
        ("stdout", "true"),
        ("stderr", "false"),
        ("tty", "true"),
    ]


def test_attach_options_full_serialization_without_container() -> None:
    options = AttachOptions(stdin=True, stdout=True, stderr=True, tty=False)
    params = options.to_query_params()
    assert params == [
        ("stdin", "true"),
        ("stdout", "true"),
        ("stderr", "true"),
        ("tty", "false"),
    ]
