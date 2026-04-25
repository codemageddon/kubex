from typing import cast

from kubex.api import Api
from kubex.client import create_client
from kubex.k8s.v1_35.apps.v1.deployment import Deployment
from kubex.k8s.v1_35.apps.v1.deployment_spec import DeploymentSpec
from kubex.k8s.v1_35.core.v1.container import Container
from kubex.k8s.v1_35.core.v1.pod_spec import PodSpec
from kubex.k8s.v1_35.core.v1.pod_template_spec import PodTemplateSpec
from kubex.k8s.v1_35.meta.v1.label_selector import LabelSelector
from kubex_core.models.metadata import ObjectMetadata
from kubex_core.models.scale import ScaleSpec

NAMESPACE = "default"


async def main() -> None:
    client = await create_client()
    async with client:
        api: Api[Deployment] = Api(Deployment, client=client, namespace=NAMESPACE)

        deployment = await api.create(
            Deployment(
                metadata=ObjectMetadata(
                    name="example-scale",
                    labels={"app": "example-scale"},
                ),
                spec=DeploymentSpec(
                    replicas=1,
                    selector=LabelSelector(match_labels={"app": "example-scale"}),
                    template=PodTemplateSpec(
                        metadata=ObjectMetadata(labels={"app": "example-scale"}),
                        spec=PodSpec(
                            containers=[Container(name="nginx", image="nginx:latest")],
                        ),
                    ),
                ),
            ),
        )
        name = cast(str, deployment.metadata.name)

        try:
            # Read current scale
            current_scale = await api.scale.get(name)
            print(f"Current replicas: {current_scale.spec.replicas}")

            # Replace scale to 3 replicas
            current_scale.spec = ScaleSpec(replicas=3)
            updated_scale = await api.scale.replace(name, current_scale)
            print(f"Updated replicas: {updated_scale.spec.replicas}")

            # Read scale again to confirm
            final_scale = await api.scale.get(name)
            print(f"Confirmed replicas: {final_scale.spec.replicas}")
        finally:
            await api.delete(name)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
