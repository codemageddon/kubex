from __future__ import annotations

import codecs
import os
import subprocess
import sys
import typing

import anyio
from anyio.abc import ByteReceiveStream
from pydantic import Field, ValidationError

from kubex.configuration.configuration import (
    ConfigModel,
    ExecConfig,
    ExecInteractiveMode,
    describe_validation_error,
)
from kubex.core.exceptions import ConfigurationError, ConfigurationValueError

SUPPORTED_EXEC_API_VERSIONS = (
    "client.authentication.k8s.io/v1",
    "client.authentication.k8s.io/v1beta1",
)
# How much of the plugin's stderr is kept for the error raised on a non-zero exit.
_STDERR_TAIL_BYTES = 8192


class ExecCredentialStatus(ConfigModel):
    expiration_timestamp: str | None = Field(None, alias="expirationTimestamp")
    token: str | None = Field(None, repr=False)
    client_certificate_data: str | None = Field(None, alias="clientCertificateData")
    client_key_data: str | None = Field(None, alias="clientKeyData", repr=False)


class ExecCredentialCluster(ConfigModel):
    """Cluster connection details passed to a plugin with `provideClusterInfo: true`."""

    server: str
    tls_server_name: str | None = Field(None, alias="tls-server-name")
    insecure_skip_tls_verify: bool | None = Field(
        None, alias="insecure-skip-tls-verify"
    )
    certificate_authority_data: str | None = Field(
        None, alias="certificate-authority-data"
    )
    """Base64-encoded PEM CA bundle."""
    proxy_url: str | None = Field(None, alias="proxy-url")
    disable_compression: bool | None = Field(None, alias="disable-compression")
    config: typing.Any = Field(None, repr=False)
    """The cluster's `client.authentication.k8s.io/exec` extension, if any."""


class ExecCredentialSpec(ConfigModel):
    cluster: ExecCredentialCluster | None = None
    interactive: bool | None = None


class ExecCredential(ConfigModel):
    api_version: str = Field(alias="apiVersion")
    kind: str
    spec: ExecCredentialSpec | None = None
    status: ExecCredentialStatus | None = None


def _stdin_is_terminal() -> bool:
    try:
        return sys.stdin is not None and sys.stdin.isatty()
    except (AttributeError, ValueError):
        return False


class _StderrRelay:
    """Copy a plugin's stderr to ours as it arrives, keeping a bounded tail.

    Plugins print interactive prompts and device-code instructions to stderr,
    so it has to reach the user while the plugin is still running.
    """

    def __init__(self) -> None:
        self.tail = bytearray()
        self._decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")

    def write(self, chunk: bytes) -> None:
        self.tail += chunk
        del self.tail[:-_STDERR_TAIL_BYTES]
        target = sys.stderr
        if target is None:
            return
        try:
            buffer = getattr(target, "buffer", None)
            if buffer is not None:
                target.flush()
                buffer.write(chunk)
                buffer.flush()
            else:
                target.write(self._decoder.decode(chunk))
                target.flush()
        except Exception:
            # A closed, broken or non-standard stderr must not fail authentication.
            pass


async def _collect(stream: ByteReceiveStream, sink: bytearray) -> None:
    async for chunk in stream:
        sink.extend(chunk)


async def _relay(stream: ByteReceiveStream, relay: _StderrRelay) -> None:
    async for chunk in stream:
        relay.write(chunk)


class ExecAuthProvider:
    def __init__(
        self,
        config: ExecConfig,
        cluster_info: ExecCredentialCluster | None = None,
    ) -> None:
        """Run a client-go credential plugin.

        Args:
            config: The kubeconfig `exec` block.
            cluster_info: Sent to the plugin in `KUBERNETES_EXEC_INFO` when
                `config.provide_cluster_info` is set.
        """
        if not config.command:
            raise ConfigurationError("exec: no command configured")
        if config.api_version not in SUPPORTED_EXEC_API_VERSIONS:
            raise ConfigurationError(
                f"exec: unsupported apiVersion {config.api_version!r}; expected one "
                f"of {list(SUPPORTED_EXEC_API_VERSIONS)}"
            )
        self.config = config
        self.cluster_info = cluster_info
        self.env = os.environ.copy()
        for item in config.env or []:
            self.env[item["name"]] = item["value"]

    def _interactive(self) -> bool:
        mode = self.config.interactive_mode or ExecInteractiveMode.IF_AVAILABLE
        if mode == ExecInteractiveMode.NEVER:
            return False
        is_terminal = _stdin_is_terminal()
        if mode == ExecInteractiveMode.ALWAYS and not is_terminal:
            raise ConfigurationValueError("Interactive mode is required")
        return is_terminal

    async def run(self) -> ExecCredential:
        interactive = self._interactive()
        cluster = self.cluster_info if self.config.provide_cluster_info else None
        kubernetes_exec_info = ExecCredential(
            api_version=typing.cast(str, self.config.api_version),
            kind=self.config.kind,
            spec=ExecCredentialSpec(cluster=cluster, interactive=interactive),
        )
        args = [self.config.command, *(self.config.args or [])]
        self.env["KUBERNETES_EXEC_INFO"] = kubernetes_exec_info.model_dump_json(
            by_alias=True, exclude_none=True
        )
        stderr = _StderrRelay()
        stdout = bytearray()
        try:
            process = await anyio.open_process(
                args,
                env=self.env,
                # client-go only connects the plugin to the user's terminal
                # when it runs interactively.
                stdin=None if interactive else subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        except FileNotFoundError:
            msg = f"exec: executable {self.config.command!r} not found"
            if self.config.install_hint:
                msg += f"\n\n{self.config.install_hint}"
            raise ConfigurationError(msg) from None
        async with process:
            if process.stdout is None or process.stderr is None:
                raise RuntimeError("exec: plugin output streams are not available")
            async with anyio.create_task_group() as tg:
                tg.start_soon(_collect, process.stdout, stdout)
                tg.start_soon(_relay, process.stderr, stderr)
            exit_code = await process.wait()
        if exit_code != 0:
            msg = f"exec: process returned {exit_code}"
            if stderr.tail:
                msg += f". {stderr.tail.decode(errors='replace').strip()}"
            raise ConfigurationValueError(msg)
        try:
            return ExecCredential.model_validate_json(bytes(stdout))
        except ValidationError as exc:
            raise ConfigurationError(
                f"exec: plugin {self.config.command!r} returned an invalid "
                f"ExecCredential: {describe_validation_error(exc)}"
            ) from None

    async def refresh_token(self) -> tuple[str, str | None]:
        """Return the credential token and its RFC 3339 `expirationTimestamp`, if the plugin reported one."""
        credential = await self.run()
        status = credential.status
        if status is not None and status.token:
            return status.token, status.expiration_timestamp
        if status is not None and (
            status.client_certificate_data or status.client_key_data
        ):
            raise ConfigurationError(
                f"exec: plugin {self.config.command!r} returned a client certificate "
                "(clientCertificateData/clientKeyData); certificate-based exec "
                "credentials are not supported yet, only token-based ones"
            )
        raise ConfigurationValueError("exec: token not found in response")
