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


async def _create_pod(
    api: Api[Pod], name: str, namespace: str, command: list[str]
) -> Pod:
    return await api.create(
        Pod(
            metadata=ObjectMetadata(name=name, namespace=namespace),
            spec=PodSpec(
                containers=[
                    Container(
                        name="main",
                        image=_BUSYBOX_IMAGE,
                        command=command,
                        stdin=True,
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
async def test_attach_observes_stdout_from_running_process(
    client: BaseClient, tmp_namespace_name: str
) -> None:
    api: Api[Pod] = Api(Pod, client=client, namespace=tmp_namespace_name)
    await _create_pod(
        api,
        "attach-stdout",
        tmp_namespace_name,
        ["sh", "-c", "while true; do echo tick; sleep 1; done"],
    )
    await _wait_for_running(api, "attach-stdout", tmp_namespace_name)

    with anyio.fail_after(30):
        async with api.attach.stream("attach-stdout", stdout=True) as session:
            buf = await _read_until(session.stdout, b"tick", timeout=15.0)

    assert b"tick" in buf


@pytest.mark.anyio
async def test_attach_stdin_writes_and_observes_echo(
    client: BaseClient, tmp_namespace_name: str
) -> None:
    api: Api[Pod] = Api(Pod, client=client, namespace=tmp_namespace_name)
    await _create_pod(
        api,
        "attach-stdin",
        tmp_namespace_name,
        ["sh", "-c", 'while IFS= read -r line; do echo "got: $line"; done'],
    )
    await _wait_for_running(api, "attach-stdin", tmp_namespace_name)

    with anyio.fail_after(30):
        async with api.attach.stream(
            "attach-stdin",
            stdin=True,
            stdout=True,
        ) as session:
            await session.stdin.write(b"hello\n")
            output = await _read_until(session.stdout, b"got: hello", timeout=10.0)

    assert b"got: hello" in output


@pytest.mark.anyio
async def test_attach_tty_true_closes_stderr_immediately(
    client: BaseClient, tmp_namespace_name: str
) -> None:
    api: Api[Pod] = Api(Pod, client=client, namespace=tmp_namespace_name)
    await _create_pod(
        api,
        "attach-tty",
        tmp_namespace_name,
        ["sh", "-c", "while true; do echo tick; sleep 1; done"],
    )
    await _wait_for_running(api, "attach-tty", tmp_namespace_name)

    with anyio.fail_after(15):
        async with api.attach.stream("attach-tty", stdout=True, tty=True) as session:
            with anyio.fail_after(5):
                # When tty=True the session closes the stderr receive stream immediately
                # (kubelet merges stderr into stdout; no stderr channel is opened).
                async for _ in session.stderr:
                    pass


@pytest.mark.anyio
async def test_attach_disconnect_does_not_kill_pod(
    client: BaseClient, tmp_namespace_name: str
) -> None:
    api: Api[Pod] = Api(Pod, client=client, namespace=tmp_namespace_name)
    await _create_pod(
        api,
        "attach-keep-alive",
        tmp_namespace_name,
        ["sh", "-c", "while true; do echo tick; sleep 1; done"],
    )
    await _wait_for_running(api, "attach-keep-alive", tmp_namespace_name)

    with anyio.fail_after(30):
        async with api.attach.stream("attach-keep-alive", stdout=True) as session:
            with anyio.fail_after(10):
                async for _ in session.stdout:
                    break  # read one chunk then disconnect

    with anyio.fail_after(10):
        pod = await api.get("attach-keep-alive", namespace=tmp_namespace_name)
    assert pod.status is not None
    assert pod.status.phase == "Running"


@pytest.mark.anyio
async def test_attach_nonexistent_pod_raises_kubex_client_exception(
    client: BaseClient, tmp_namespace_name: str
) -> None:
    api: Api[Pod] = Api(Pod, client=client, namespace=tmp_namespace_name)
    with pytest.raises(KubexClientException):
        async with api.attach.stream("does-not-exist") as _:
            pass
