from typing import cast

from kubex.api import Api
from kubex.client import create_client
from kubex.core.exceptions import Conflict, KubexApiError, NotFound
from kubex.k8s.v1_35.core.v1.container import Container
from kubex.k8s.v1_35.core.v1.pod import Pod
from kubex.k8s.v1_35.core.v1.pod_spec import PodSpec
from kubex_core.models.metadata import ObjectMetadata
from kubex_core.models.status import Status

NAMESPACE = "default"


async def main() -> None:
    client = await create_client()
    async with client:
        api: Api[Pod] = Api(Pod, client=client, namespace=NAMESPACE)

        pod = await api.create(
            Pod(
                metadata=ObjectMetadata(
                    name="example-error-handling",
                    labels={"app": "example"},
                ),
                spec=PodSpec(
                    containers=[Container(name="nginx", image="nginx:latest")]
                ),
            ),
        )
        name = cast(str, pod.metadata.name)

        try:
            # NotFound: try to get a pod that does not exist
            try:
                await api.get("non-existent-pod")
            except NotFound as e:
                print(f"NotFound caught: status={e.status}")
                if isinstance(e.content, Status):
                    print(f"  reason: {e.content.reason}, message: {e.content.message}")
                else:
                    print(f"  content: {e.content}")

            # Conflict: try to create a pod that already exists
            try:
                await api.create(
                    Pod(
                        metadata=ObjectMetadata(name=name),
                        spec=PodSpec(
                            containers=[Container(name="nginx", image="nginx:latest")]
                        ),
                    ),
                )
            except Conflict as e:
                print(f"Conflict caught: status={e.status}")

            # KubexApiError: catch any API error generically
            try:
                await api.get("another-non-existent-pod")
            except KubexApiError as e:
                print(
                    f"KubexApiError caught: status={e.status}, type={type(e).__name__}"
                )
        finally:
            await api.delete(name)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
