import pytest

from kubex.configuration.auth.exec import ExecAuthProvider
from kubex.configuration.configuration import ExecConfig, ExecInteractiveMode


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
    assert result.status.token == "test-token"
