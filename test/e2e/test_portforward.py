from __future__ import annotations

import socket

import anyio
import anyio.abc
import pytest

from kubex.api import Api
from kubex.client import BaseClient
from kubex.k8s.v1_35.core.v1.container import Container
from kubex.k8s.v1_35.core.v1.pod import Pod
from kubex.k8s.v1_35.core.v1.pod_spec import PodSpec
from kubex_core.models.metadata import ObjectMetadata


_NGINX_IMAGE = "nginx:alpine"
_HTTP_REQUEST = b"GET / HTTP/1.0\r\nHost: localhost\r\n\r\n"


async def _create_nginx_pod(api: Api[Pod], name: str, namespace: str) -> Pod:
    return await api.create(
        Pod(
            metadata=ObjectMetadata(name=name, namespace=namespace),
            spec=PodSpec(containers=[Container(name="nginx", image=_NGINX_IMAGE)]),
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


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


async def _read_bytes(stream: anyio.abc.ByteStream, *, timeout: float = 15.0) -> bytes:
    buf = bytearray()
    with anyio.fail_after(timeout):
        try:
            while True:
                chunk = await stream.receive()
                buf.extend(chunk)
        except (anyio.EndOfStream, anyio.ClosedResourceError):
            pass
    return bytes(buf)


@pytest.mark.anyio
async def test_portforward_forward_http_get_returns_200(
    client: BaseClient, tmp_namespace_name: str
) -> None:
    api: Api[Pod] = Api(Pod, client=client, namespace=tmp_namespace_name)
    await _create_nginx_pod(api, "pf-fwd-nginx", tmp_namespace_name)
    await _wait_for_running(api, "pf-fwd-nginx", tmp_namespace_name)

    async with api.portforward.forward("pf-fwd-nginx", ports=[80]) as pf:
        stream = pf.streams[80]
        await stream.send(_HTTP_REQUEST)
        await stream.send_eof()
        response = await _read_bytes(stream)

    assert response.startswith(b"HTTP/1.")
    assert b"200" in response


@pytest.mark.anyio
async def test_portforward_listen_http_get_returns_200(
    client: BaseClient, tmp_namespace_name: str
) -> None:
    api: Api[Pod] = Api(Pod, client=client, namespace=tmp_namespace_name)
    await _create_nginx_pod(api, "pf-listen-nginx", tmp_namespace_name)
    await _wait_for_running(api, "pf-listen-nginx", tmp_namespace_name)

    local_port = _free_port()
    async with api.portforward.listen("pf-listen-nginx", port_map={80: local_port}):
        async with await anyio.connect_tcp("127.0.0.1", local_port) as sock:
            await sock.send(_HTTP_REQUEST)
            response = await _read_bytes(sock)

    assert response.startswith(b"HTTP/1.")
    assert b"200" in response


@pytest.mark.anyio
async def test_portforward_forward_late_reader_receives_whole_body(
    client: BaseClient, tmp_namespace_name: str
) -> None:
    """Regression: once 128 frames were queued on a port, ``forward()`` closed
    the stream and dropped the rest of the response."""
    api: Api[Pod] = Api(Pod, client=client, namespace=tmp_namespace_name)
    await _create_nginx_pod(api, "pf-fwd-big", tmp_namespace_name)
    await _wait_for_running(api, "pf-fwd-big", tmp_namespace_name)
    size = 8 << 20
    created = await api.exec.run(
        "pf-fwd-big",
        command=["sh", "-c", f"head -c {size} /dev/zero > /usr/share/nginx/html/big"],
    )
    created.raise_for_status()

    async with api.portforward.forward("pf-fwd-big", ports=[80]) as pf:
        stream = pf.streams[80]
        await stream.send(b"GET /big HTTP/1.0\r\nHost: localhost\r\n\r\n")
        await anyio.sleep(2)  # let the response pile up before reading
        response = await _read_bytes(stream, timeout=60)

    head, _, body = response.partition(b"\r\n\r\n")
    assert head.startswith(b"HTTP/1.") and b" 200 " in head
    assert len(body) == size
