import uuid

from kubex.api import Api
from kubex.client import create_client
from kubex.k8s.v1_35.core.v1.container import Container
from kubex.k8s.v1_35.core.v1.pod import Pod
from kubex.k8s.v1_35.core.v1.pod_spec import PodSpec
from kubex_core.models.metadata import ObjectMetadata

NAMESPACE = "default"


async def main() -> None:
    client = await create_client()
    async with client:
        api: Api[Pod] = Api(Pod, client=client, namespace=NAMESPACE)

        # Use a unique label value per run to avoid deleting unrelated pods
        run_id = uuid.uuid4().hex[:8]
        label_selector = f"app=example-batch-{run_id}"

        try:
            # Create several pods with the same label
            for i in range(3):
                await api.create(
                    Pod(
                        metadata=ObjectMetadata(
                            generate_name=f"example-delete-collection-{i}-",
                            labels={"app": f"example-batch-{run_id}"},
                        ),
                        spec=PodSpec(
                            containers=[Container(name="nginx", image="nginx:latest")]
                        ),
                    ),
                )
            print(f"Created 3 pods with label {label_selector}")

            pods = await api.list(label_selector=label_selector)
            print(f"Listed {len(pods.items)} pods before delete_collection")

            # Delete all pods matching the label selector
            result = await api.delete_collection(label_selector=label_selector)
            print(f"delete_collection result: {type(result).__name__}")
        finally:
            # Ensure cleanup of any pods created with our label
            await api.delete_collection(label_selector=label_selector)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
