from __future__ import annotations

import anyio
import pytest

from kubex.api import Api
from kubex.client import BaseClient
from kubex.core.exceptions import KubexClientException
from kubex.k8s.v1_35.core.v1.container import Container
from kubex.k8s.v1_35.core.v1.pod import Pod
from kubex.k8s.v1_35.core.v1.pod_spec import PodSpec
from kubex_core.models.metadata import ObjectMetadata


_BUSYBOX_IMAGE = "busybox:1.36"


async def _create_busybox_pod(api: Api[Pod], name: str, namespace: str) -> Pod:
    return await api.create(
        Pod(
            metadata=ObjectMetadata(name=name, namespace=namespace),
            spec=PodSpec(
                containers=[
                    Container(
                        name="main",
                        image=_BUSYBOX_IMAGE,
                        command=["sleep", "3600"],
                    )
                ]
            ),
        ),
        namespace=namespace,
    )


async def _wait_for_running(
    api: Api[Pod],
    name: str,
    namespace: str,
    timeout: int = 300,
) -> Pod:
    pod = await api.get(name, namespace=namespace)
    if pod.status is not None and pod.status.phase == "Running":
        return pod

    resource_version = pod.metadata.resource_version if pod.metadata else None
    async for event in api.watch(
        field_selector=f"metadata.name={name}",
        namespace=namespace,
        resource_version=resource_version,
        timeout_seconds=timeout,
        request_timeout=timeout,
    ):
        obj = event.object
        if (
            isinstance(obj, Pod)
            and obj.status is not None
            and obj.status.phase == "Running"
        ):
            return obj

    raise TimeoutError(f"Pod {name} did not reach Running within {timeout}s")


async def _read_until(
    stream: anyio.abc.ObjectReceiveStream[bytes],
    needle: bytes,
    *,
    timeout: float = 10.0,
) -> bytes:
    buf = bytearray()
    with anyio.fail_after(timeout):
        async for chunk in stream:
            buf.extend(chunk)
            if needle in buf:
                return bytes(buf)
    return bytes(buf)


@pytest.mark.anyio
async def test_exec_run_echo_returns_stdout_and_zero_exit(
    client: BaseClient, tmp_namespace_name: str
) -> None:
    api: Api[Pod] = Api(Pod, client=client, namespace=tmp_namespace_name)
    await _create_busybox_pod(api, "exec-echo", tmp_namespace_name)
    await _wait_for_running(api, "exec-echo", tmp_namespace_name)

    result = await api.exec.run("exec-echo", command=["echo", "hello"])
    assert result.stdout == b"hello\n"
    assert result.exit_code == 0


@pytest.mark.anyio
async def test_exec_run_non_zero_exit_code_is_reported(
    client: BaseClient, tmp_namespace_name: str
) -> None:
    api: Api[Pod] = Api(Pod, client=client, namespace=tmp_namespace_name)
    await _create_busybox_pod(api, "exec-exit-code", tmp_namespace_name)
    await _wait_for_running(api, "exec-exit-code", tmp_namespace_name)

    result = await api.exec.run("exec-exit-code", command=["sh", "-c", "exit 7"])
    assert result.exit_code == 7
    assert result.status is not None
    assert result.status.status == "Failure"


@pytest.mark.anyio
async def test_exec_run_pipes_stdin_to_command(
    client: BaseClient, tmp_namespace_name: str
) -> None:
    api: Api[Pod] = Api(Pod, client=client, namespace=tmp_namespace_name)
    await _create_busybox_pod(api, "exec-stdin", tmp_namespace_name)
    await _wait_for_running(api, "exec-stdin", tmp_namespace_name)

    result = await api.exec.run("exec-stdin", command=["cat"], stdin=b"piped\n")
    assert result.stdout == b"piped\n"


@pytest.mark.anyio
async def test_exec_stream_interactive_shell(
    client: BaseClient, tmp_namespace_name: str
) -> None:
    api: Api[Pod] = Api(Pod, client=client, namespace=tmp_namespace_name)
    await _create_busybox_pod(api, "exec-stream-sh", tmp_namespace_name)
    await _wait_for_running(api, "exec-stream-sh", tmp_namespace_name)

    async with api.exec.stream(
        "exec-stream-sh",
        command=["sh"],
        stdin=True,
        stdout=True,
        stderr=True,
        tty=True,
    ) as session:
        await session.stdin.write(b"echo MARK-$$\n")
        output = await _read_until(session.stdout, b"MARK-")
        assert b"MARK-" in output

        await session.stdin.write(b"exit 0\n")
        # Drain remaining output until the shell closes the channel.
        with anyio.fail_after(15):
            async for _ in session.stdout:
                pass

        status = await session.wait_for_status()
    assert status is not None
    assert status.status == "Success"


@pytest.mark.anyio
async def test_exec_stream_resize_changes_terminal_size(
    client: BaseClient, tmp_namespace_name: str
) -> None:
    api: Api[Pod] = Api(Pod, client=client, namespace=tmp_namespace_name)
    await _create_busybox_pod(api, "exec-resize", tmp_namespace_name)
    await _wait_for_running(api, "exec-resize", tmp_namespace_name)

    async with api.exec.stream(
        "exec-resize",
        command=["sh"],
        stdin=True,
        stdout=True,
        stderr=True,
        tty=True,
    ) as session:
        await session.resize(width=120, height=40)
        # Give the kernel a moment to apply the SIGWINCH.
        await anyio.sleep(0.5)
        await session.stdin.write(b"stty size; exit 0\n")

        buf = bytearray()
        with anyio.fail_after(15):
            async for chunk in session.stdout:
                buf.extend(chunk)
        # `stty size` prints "rows cols" (e.g. "40 120").
        assert b"40 120" in bytes(buf)


@pytest.mark.anyio
async def test_exec_against_missing_container_reports_failure(
    client: BaseClient, tmp_namespace_name: str
) -> None:
    api: Api[Pod] = Api(Pod, client=client, namespace=tmp_namespace_name)
    await _create_busybox_pod(api, "exec-missing-container", tmp_namespace_name)
    await _wait_for_running(api, "exec-missing-container", tmp_namespace_name)

    try:
        result = await api.exec.run(
            "exec-missing-container",
            command=["true"],
            container="does-not-exist",
        )
    except KubexClientException as exc:
        # Some Kubernetes versions reject the upgrade outright with a 4xx
        # handshake response. The current adapter only surfaces the status
        # line, so anchor on that to make sure a bug elsewhere in the
        # WebSocket layer cannot masquerade as a pass for this test.
        message = str(exc).lower()
        assert "handshake" in message
        assert "400" in message or "404" in message or "does-not-exist" in message
        return
    # Otherwise the server should report a failure on the error channel.
    assert result.status is not None
    assert result.status.status == "Failure"
