from __future__ import annotations

import anyio
import pytest

from kubex.api import Api
from kubex.api._exec import ExecError
from kubex.client import BaseClient
from kubex.core.exceptions import BadRequest
from kubex.k8s.v1_35.core.v1.pod import Pod
from test.e2e._helpers import create_busybox_pod, wait_for_pod_running


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
    await create_busybox_pod(api, "exec-echo", tmp_namespace_name)
    await wait_for_pod_running(api, "exec-echo", tmp_namespace_name)

    result = await api.exec.run("exec-echo", command=["echo", "hello"])
    assert result.stdout == b"hello\n"
    assert result.exit_code == 0


@pytest.mark.anyio
async def test_exec_run_non_zero_exit_code_is_reported(
    client: BaseClient, tmp_namespace_name: str
) -> None:
    api: Api[Pod] = Api(Pod, client=client, namespace=tmp_namespace_name)
    await create_busybox_pod(api, "exec-exit-code", tmp_namespace_name)
    await wait_for_pod_running(api, "exec-exit-code", tmp_namespace_name)

    result = await api.exec.run("exec-exit-code", command=["sh", "-c", "exit 7"])
    assert result.exit_code == 7
    assert result.status is not None
    assert result.status.status == "Failure"


@pytest.mark.anyio
async def test_exec_run_pipes_stdin_to_command(
    client: BaseClient, tmp_namespace_name: str
) -> None:
    api: Api[Pod] = Api(Pod, client=client, namespace=tmp_namespace_name)
    await create_busybox_pod(api, "exec-stdin", tmp_namespace_name)
    await wait_for_pod_running(api, "exec-stdin", tmp_namespace_name)

    result = await api.exec.run("exec-stdin", command=["cat"], stdin=b"piped\n")
    assert result.stdout == b"piped\n"


@pytest.mark.anyio
async def test_exec_stream_interactive_shell(
    client: BaseClient, tmp_namespace_name: str
) -> None:
    api: Api[Pod] = Api(Pod, client=client, namespace=tmp_namespace_name)
    await create_busybox_pod(api, "exec-stream-sh", tmp_namespace_name)
    await wait_for_pod_running(api, "exec-stream-sh", tmp_namespace_name)

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
    await create_busybox_pod(api, "exec-resize", tmp_namespace_name)
    await wait_for_pod_running(api, "exec-resize", tmp_namespace_name)

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
async def test_exec_against_missing_container_raises_bad_request(
    client: BaseClient, tmp_namespace_name: str
) -> None:
    api: Api[Pod] = Api(Pod, client=client, namespace=tmp_namespace_name)
    await create_busybox_pod(api, "exec-missing-container", tmp_namespace_name)
    await wait_for_pod_running(api, "exec-missing-container", tmp_namespace_name)

    # The API server rejects the upgrade with 400 and a Status naming the
    # container; the handshake error is mapped to the typed exception.
    with pytest.raises(BadRequest, match="does-not-exist"):
        await api.exec.run(
            "exec-missing-container",
            command=["true"],
            container="does-not-exist",
        )


@pytest.mark.anyio
async def test_exec_stream_late_consumer_receives_all_output(
    client: BaseClient, tmp_namespace_name: str
) -> None:
    """Regression: once 128 frames were queued, the channel was closed and the
    rest of the output silently dropped while the status still said Success."""
    api: Api[Pod] = Api(Pod, client=client, namespace=tmp_namespace_name)
    await create_busybox_pod(api, "exec-late-consumer", tmp_namespace_name)
    await wait_for_pod_running(api, "exec-late-consumer", tmp_namespace_name)

    # One frame per line: the shell writes each line separately, paced.
    script = "i=0; while [ $i -lt 400 ]; do echo line$i; usleep 1000; i=$((i+1)); done"
    async with api.exec.stream(
        "exec-late-consumer", command=["sh", "-c", script], stderr=False
    ) as session:
        await anyio.sleep(2)  # let far more than 128 frames pile up
        buf = bytearray()
        with anyio.fail_after(30):
            async for chunk in session.stdout:
                buf.extend(chunk)
            status = await session.wait_for_status()

    assert bytes(buf).splitlines() == [b"line%d" % i for i in range(400)]
    assert status is not None and status.status == "Success"


@pytest.mark.anyio
async def test_exec_run_without_output_channels_reports_exit_code(
    client: BaseClient, tmp_namespace_name: str
) -> None:
    """Regression: with stdout/stderr off, the server's empty first frame on
    the error channel resolved the status at once (``exit_code=None``)."""
    api: Api[Pod] = Api(Pod, client=client, namespace=tmp_namespace_name)
    await create_busybox_pod(api, "exec-no-output", tmp_namespace_name)
    await wait_for_pod_running(api, "exec-no-output", tmp_namespace_name)

    result = await api.exec.run(
        "exec-no-output",
        command=["sh", "-c", "sleep 1; cat > /tmp/f; exit 3"],
        stdin=b"payload",
        stdout=False,
        stderr=False,
    )
    assert result.exit_code == 3

    check = await api.exec.run("exec-no-output", command=["cat", "/tmp/f"])
    assert check.stdout == b"payload"


@pytest.mark.anyio
async def test_exec_run_large_stdin_is_delivered(
    client: BaseClient, tmp_namespace_name: str
) -> None:
    """Regression: stdin went out as a single WebSocket message, which the API
    server drops above its size cap (closing with 1000, i.e. no error)."""
    api: Api[Pod] = Api(Pod, client=client, namespace=tmp_namespace_name)
    await create_busybox_pod(api, "exec-large-stdin", tmp_namespace_name)
    await wait_for_pod_running(api, "exec-large-stdin", tmp_namespace_name)

    size = 40 << 20
    result = await api.exec.run(
        "exec-large-stdin", command=["wc", "-c"], stdin=b"x" * size
    )
    assert result.stdout.strip() == str(size).encode()
    assert result.exit_code == 0


@pytest.mark.anyio
async def test_exec_raise_for_status_on_missing_binary(
    client: BaseClient, tmp_namespace_name: str
) -> None:
    api: Api[Pod] = Api(Pod, client=client, namespace=tmp_namespace_name)
    await create_busybox_pod(api, "exec-missing-binary", tmp_namespace_name)
    await wait_for_pod_running(api, "exec-missing-binary", tmp_namespace_name)

    result = await api.exec.run("exec-missing-binary", command=["/nonexistent"])
    assert result.exit_code is None
    with pytest.raises(ExecError, match="nonexistent"):
        result.raise_for_status()
