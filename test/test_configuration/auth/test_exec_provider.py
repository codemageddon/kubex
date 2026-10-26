from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import anyio
import pytest

from kubex.configuration.auth import exec as exec_module
from kubex.configuration.auth.exec import (
    ExecAuthProvider,
    ExecCredentialCluster,
    ExecCredentialStatus,
)
from kubex.configuration.configuration import ExecConfig, ExecInteractiveMode
from kubex.core.exceptions import ConfigurationError, ConfigurationValueError

V1 = "client.authentication.k8s.io/v1"


def _python_plugin(script: str, *args: str, **config: Any) -> ExecAuthProvider:
    """An exec provider whose plugin is `python -c <script> [args]`."""
    return ExecAuthProvider(
        config=ExecConfig(
            api_version=V1,
            command=sys.executable,
            args=["-c", script, *args],
            **config,
        )
    )


def _credential_json(status: dict[str, Any]) -> str:
    return json.dumps({"apiVersion": V1, "kind": "ExecCredential", "status": status})


@pytest.mark.anyio
async def test_exec_provider_run() -> None:
    provider = ExecAuthProvider(
        config=ExecConfig(
            api_version="client.authentication.k8s.io/v1",
            kind="ExecCredential",
            command="echo",
            args=[
                "-n",
                '{"apiVersion":"client.authentication.k8s.io/v1", "kind": "ExecCredential", "status": {"token": "test-token"}}',
            ],
            interactive_mode=ExecInteractiveMode.IF_AVAILABLE,
        )
    )
    result = await provider.run()
    assert result.status is not None
    assert result.status.token == "test-token"


def test_exec_provider_applies_configured_env() -> None:
    provider = ExecAuthProvider(
        config=ExecConfig(
            api_version=V1,
            command="echo",
            env=[{"name": "AWS_PROFILE", "value": "prod"}],
        )
    )
    assert provider.env["AWS_PROFILE"] == "prod"


def test_exec_provider_rejects_missing_or_unknown_api_version() -> None:
    with pytest.raises(ConfigurationError, match="apiVersion"):
        ExecAuthProvider(config=ExecConfig(command="echo"))
    with pytest.raises(ConfigurationError, match="apiVersion"):
        ExecAuthProvider(
            config=ExecConfig(
                api_version="client.authentication.k8s.io/v1alpha1", command="echo"
            )
        )


def test_exec_provider_rejects_empty_command() -> None:
    with pytest.raises(ConfigurationError, match="no command"):
        ExecAuthProvider(config=ExecConfig(api_version=V1))


@pytest.mark.anyio
async def test_exec_stderr_is_relayed_and_stdout_parsed(
    capsys: pytest.CaptureFixture[str],
) -> None:
    script = (
        "import sys\n"
        "sys.stderr.write('open https://idp.example/device and enter ABCD\\n')\n"
        f"print({_credential_json({'token': 'tok'})!r})\n"
    )
    token, _ = await _python_plugin(script).refresh_token()
    assert token == "tok"
    assert "open https://idp.example/device and enter ABCD" in capsys.readouterr().err


class _SignallingStderr:
    """A stand-in for sys.stderr that creates `marker` when written to."""

    def __init__(self, marker: Path) -> None:
        self.marker = marker
        self.buffer = self
        self.written = b""

    def write(self, data: bytes) -> int:
        self.written += data
        self.marker.touch()
        return len(data)

    def flush(self) -> None:
        pass


@pytest.mark.anyio
async def test_exec_stderr_is_relayed_while_plugin_runs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The plugin only exits after the test has seen its prompt, so this
    # deadlocks (and times out) unless stderr is relayed live.
    marker = tmp_path / "prompt-seen"
    fake_stderr = _SignallingStderr(marker)
    monkeypatch.setattr(sys, "stderr", fake_stderr)
    script = (
        "import os, sys, time\n"
        "sys.stderr.write('enter code\\n'); sys.stderr.flush()\n"
        "deadline = time.monotonic() + 10\n"
        "while not os.path.exists(sys.argv[1]):\n"
        "    if time.monotonic() > deadline: sys.exit(3)\n"
        "    time.sleep(0.01)\n"
        f"print({_credential_json({'token': 'after-prompt'})!r})\n"
    )
    with anyio.fail_after(20):
        token, _ = await _python_plugin(script, str(marker)).refresh_token()
    assert token == "after-prompt"
    assert fake_stderr.written == b"enter code\n"


@pytest.mark.anyio
async def test_exec_nonzero_exit_reports_bounded_stderr_tail(
    capsys: pytest.CaptureFixture[str],
) -> None:
    script = (
        "import sys\n"
        "sys.stderr.write('x' * 50000)\n"
        "sys.stderr.write('LAST-LINE')\n"
        "sys.exit(7)\n"
    )
    with pytest.raises(
        ConfigurationValueError, match="exec: process returned 7"
    ) as exc_info:
        await _python_plugin(script).run()
    message = str(exc_info.value)
    assert message.endswith("LAST-LINE")
    assert len(message) < 9000
    capsys.readouterr()


@pytest.mark.anyio
async def test_exec_non_interactive_plugin_gets_no_stdin() -> None:
    script = (
        "import sys\n"
        "data = sys.stdin.read()\n"
        "import json\n"
        "print(json.dumps({'apiVersion': 'client.authentication.k8s.io/v1',"
        " 'kind': 'ExecCredential', 'status': {'token': 'stdin-' + str(len(data))}}))\n"
    )
    with anyio.fail_after(20):
        token, _ = await _python_plugin(
            script, interactive_mode=ExecInteractiveMode.NEVER
        ).refresh_token()
    assert token == "stdin-0"


@pytest.mark.anyio
async def test_exec_interactive_mode_defaults_to_if_available(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    script = (
        "import json, os\n"
        "info = json.loads(os.environ['KUBERNETES_EXEC_INFO'])\n"
        "print(json.dumps({'apiVersion': 'client.authentication.k8s.io/v1',"
        " 'kind': 'ExecCredential',"
        " 'status': {'token': str(info['spec']['interactive'])}}))\n"
    )
    provider = _python_plugin(script)
    monkeypatch.setattr(exec_module, "_stdin_is_terminal", lambda: False)
    assert (await provider.refresh_token())[0] == "False"
    # Only the reported flag is checked here: a real terminal stdin can't be
    # faked for the child, so stdin itself stays inherited from the test run.
    monkeypatch.setattr(exec_module, "_stdin_is_terminal", lambda: True)
    assert provider._interactive() is True


def test_exec_always_interactive_requires_terminal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(exec_module, "_stdin_is_terminal", lambda: False)
    provider = _python_plugin("", interactive_mode=ExecInteractiveMode.ALWAYS)
    with pytest.raises(ConfigurationValueError, match="Interactive mode is required"):
        provider._interactive()


@pytest.mark.anyio
async def test_exec_client_certificate_credential_is_rejected_clearly() -> None:
    script = "print({!r})".format(
        _credential_json(
            {
                "clientCertificateData": "-----BEGIN CERTIFICATE-----",
                "clientKeyData": "-----BEGIN PRIVATE KEY-----",
            }
        )
    )
    with pytest.raises(ConfigurationError, match="not supported yet"):
        await _python_plugin(script).refresh_token()


@pytest.mark.anyio
async def test_exec_missing_token_raises_configuration_value_error() -> None:
    script = "print({!r})".format(_credential_json({}))
    with pytest.raises(ConfigurationValueError, match="token not found"):
        await _python_plugin(script).refresh_token()


@pytest.mark.anyio
@pytest.mark.parametrize(
    "output",
    [
        # Missing apiVersion: pydantic's message would echo the whole object.
        '{"kind": "ExecCredential", "status": {"token": "SUPER-SECRET-TOKEN"}}',
        "SUPER-SECRET-TOKEN is not JSON",
    ],
)
async def test_exec_invalid_output_does_not_leak_secrets(output: str) -> None:
    with pytest.raises(ConfigurationError, match="invalid ExecCredential") as exc_info:
        await _python_plugin(f"print({output!r})").run()
    assert "SUPER-SECRET-TOKEN" not in str(exc_info.value)
    assert exc_info.value.__cause__ is None
    assert exc_info.value.__suppress_context__


@pytest.mark.anyio
async def test_exec_missing_executable_reports_install_hint(tmp_path: Path) -> None:
    provider = ExecAuthProvider(
        config=ExecConfig(
            api_version=V1,
            command=str(tmp_path / "no-such-plugin"),
            install_hint="Install it with: brew install no-such-plugin",
        )
    )
    with pytest.raises(ConfigurationError, match="not found") as exc_info:
        await provider.run()
    assert "brew install no-such-plugin" in str(exc_info.value)


_ECHO_EXEC_INFO = (
    "import json, os, sys\n"
    "open(sys.argv[1], 'w').write(os.environ['KUBERNETES_EXEC_INFO'])\n"
    "print(json.dumps({'apiVersion': 'client.authentication.k8s.io/v1',"
    " 'kind': 'ExecCredential', 'status': {'token': 't'}}))\n"
)


@pytest.mark.anyio
async def test_exec_provide_cluster_info_passes_spec_cluster(tmp_path: Path) -> None:
    out = tmp_path / "exec-info.json"
    provider = ExecAuthProvider(
        config=ExecConfig(
            api_version=V1,
            command=sys.executable,
            args=["-c", _ECHO_EXEC_INFO, str(out)],
            provide_cluster_info=True,
            interactive_mode=ExecInteractiveMode.NEVER,
        ),
        cluster_info=ExecCredentialCluster(
            server="https://h:6443",
            certificate_authority_data="UEVN",
            config={"audience": "kubex"},
        ),
    )
    await provider.refresh_token()
    assert json.loads(out.read_text()) == {
        "apiVersion": V1,
        "kind": "ExecCredential",
        "spec": {
            "cluster": {
                "server": "https://h:6443",
                "certificate-authority-data": "UEVN",
                "config": {"audience": "kubex"},
            },
            "interactive": False,
        },
    }


@pytest.mark.anyio
async def test_exec_cluster_info_omitted_without_provide_cluster_info(
    tmp_path: Path,
) -> None:
    out = tmp_path / "exec-info.json"
    provider = ExecAuthProvider(
        config=ExecConfig(
            api_version=V1,
            command=sys.executable,
            args=["-c", _ECHO_EXEC_INFO, str(out)],
            interactive_mode=ExecInteractiveMode.NEVER,
        ),
        cluster_info=ExecCredentialCluster(server="https://h:6443"),
    )
    await provider.refresh_token()
    assert "cluster" not in json.loads(out.read_text())["spec"]


def test_exec_credential_status_repr_hides_secrets() -> None:
    status = ExecCredentialStatus(token="TOKEN-VALUE", client_key_data="KEY-VALUE")
    assert "TOKEN-VALUE" not in repr(status)
    assert "KEY-VALUE" not in repr(status)
