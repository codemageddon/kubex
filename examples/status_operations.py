from typing import cast

from kubex.api import Api
from kubex.client import create_client
from kubex.k8s.v1_35.apps.v1.deployment import Deployment
from kubex.k8s.v1_35.apps.v1.deployment_spec import DeploymentSpec
from kubex.k8s.v1_35.apps.v1.deployment_status import DeploymentStatus
from kubex.k8s.v1_35.core.v1.container import Container
from kubex.k8s.v1_35.core.v1.pod_spec import PodSpec
from kubex.k8s.v1_35.core.v1.pod_template_spec import PodTemplateSpec
from kubex.k8s.v1_35.meta.v1.label_selector import LabelSelector
from kubex_core.models.metadata import ObjectMetadata

NAMESPACE = "default"


async def main() -> None:
    client = await create_client()
    async with client:
        api: Api[Deployment] = Api(Deployment, client=client, namespace=NAMESPACE)

        deployment = await api.create(
            Deployment(
                metadata=ObjectMetadata(
                    name="example-status",
                    labels={"app": "example-status"},
                ),
                spec=DeploymentSpec(
                    replicas=1,
                    selector=LabelSelector(match_labels={"app": "example-status"}),
                    template=PodTemplateSpec(
                        metadata=ObjectMetadata(labels={"app": "example-status"}),
                        spec=PodSpec(
                            containers=[Container(name="nginx", image="nginx:latest")],
                        ),
                    ),
                ),
            ),
        )
        name = cast(str, deployment.metadata.name)

        try:
            # Read the status subresource
            current = await api.status.get(name)
            print(
                f"Status: replicas={current.status and current.status.replicas}, "
                f"available={current.status and current.status.available_replicas}"
            )

            # Replace status (typically done by controllers, shown here for
            # demonstration)
            current.status = DeploymentStatus(replicas=1, available_replicas=1)
            updated = await api.status.replace(name, current)
            print(
                f"After replace: "
                f"replicas={updated.status and updated.status.replicas}, "
                f"available={updated.status and updated.status.available_replicas}"
            )
        finally:
            await api.delete(name)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
