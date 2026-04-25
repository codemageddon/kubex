import asyncio
from typing import cast

import anyio

from kubex.api import Api
from kubex.client import create_client
from kubex.k8s.v1_35.core.v1.container import Container
from kubex.k8s.v1_35.core.v1.pod import Pod
from kubex.k8s.v1_35.core.v1.pod_spec import PodSpec
from kubex_core.models.metadata import ObjectMetadata

NAMESPACE = "default"


async def _wait_for_running(api: Api[Pod], name: str, timeout: int = 120) -> None:
    pod = await api.get(name)
    if pod.status is not None and pod.status.phase == "Running":
        return
    resource_version = pod.metadata.resource_version if pod.metadata else None
    async for event in api.watch(
        field_selector=f"metadata.name={name}",
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
            return
    raise TimeoutError(f"Pod {name} did not reach Running within {timeout}s")


async def main() -> None:
    client = await create_client()
    async with client:
        api: Api[Pod] = Api(Pod, client=client, namespace=NAMESPACE)
        pod = await api.create(
            Pod(
                metadata=ObjectMetadata(generate_name="example-exec-"),
                spec=PodSpec(
                    containers=[
                        Container(
                            name="main",
                            image="busybox:1.36",
                            command=["sleep", "3600"],
                        )
                    ]
                ),
            ),
        )
        pod_name = cast(str, pod.metadata.name)
        try:
            await _wait_for_running(api, pod_name)

            # 1. One-shot: capture stdout/stderr and exit code from a single command.
            result = await api.exec.run(pod_name, command=["ls", "-la", "/"])
            print(f"exit code: {result.exit_code}")
            print(result.stdout.decode())
            if result.stderr:
                print("stderr:", result.stderr.decode())

            # 2. Interactive: open a TTY shell, write commands, resize, then exit.
            async with api.exec.stream(
                pod_name,
                command=["sh"],
                stdin=True,
                stdout=True,
                stderr=True,
                tty=True,
            ) as session:
                await session.resize(width=120, height=40)
                await session.stdin.write(b"echo MARK-$$\n")

                buf = bytearray()
                with anyio.fail_after(5):
                    async for chunk in session.stdout:
                        buf.extend(chunk)
                        if b"MARK-" in buf:
                            break
                print("interactive output:", bytes(buf).decode(errors="replace"))

                await session.stdin.write(b"exit 0\n")
                await session.close_stdin()

                status = await session.wait_for_status()
                print(f"session status: {status.status if status else 'unknown'}")
        finally:
            await api.delete(pod_name)


if __name__ == "__main__":
    asyncio.run(main())
