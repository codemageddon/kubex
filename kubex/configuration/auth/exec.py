import os
import sys

import anyio
from pydantic import Field

from kubex.configuration.configuration import ExecConfig, ExecInteractiveMode
from kubex.models.base import BaseK8sModel


class ExecCredentialStatus(BaseK8sModel):
    expiration_timestamp: str | None = Field(None, alias="expirationTimestamp")
    token: str | None = None
    client_certificate_data: str | None = Field(None, alias="clientCertificateData")
    client_key_data: str | None = Field(None, alias="clientKeyData")


class ExecCredentialSpec(BaseK8sModel):
    interactive: bool | None = None


class ExecCredential(BaseK8sModel):
    api_version: str = Field(alias="apiVersion")
    kind: str
    spec: ExecCredentialSpec | None = None
    status: ExecCredentialStatus | None = None


class ExecAuthProvider:
    def __init__(self, config: ExecConfig):
        self.config = config
        self.env = os.environ.copy()

    async def run(self) -> ExecCredential:
        _interactive = False
        isatty = sys.stdin.isatty()
        if self.config.interactive_mode == ExecInteractiveMode.ALWAYS:
            if not isatty:
                raise ValueError("Interactive mode is required")
            _interactive = True
        elif self.config.interactive_mode == ExecInteractiveMode.IF_AVAILABLE:
            _interactive = isatty
        kubernetes_exec_info = ExecCredential(
            api_version=self.config.api_version,
            kind=self.config.kind,
            spec=ExecCredentialSpec(interactive=_interactive),
        )

        args = [self.config.command]
        if self.config.args:
            args.extend(self.config.args)
        self.env["KUBERNETES_EXEC_INFO"] = kubernetes_exec_info.model_dump_json(
            by_alias=True, exclude_none=True, exclude_unset=True
        )
        proc = await anyio.run_process(
            command=args,
            env=self.env,
            input=None,
        )
        stdout = proc.stdout
        stderr = proc.stderr
        exit_code = proc.returncode
        if exit_code != 0:
            msg = f"exec: process returned {exit_code}"
            if stderr:
                msg += f". {stderr.decode()}"
            raise ValueError(msg)

        return ExecCredential.model_validate_json(stdout)

    async def refresh_token(self) -> str:
        credential = await self.run()
        if credential.status is None or credential.status.token is None:
            raise ValueError("exec: token not found in response")
        return credential.status.token
