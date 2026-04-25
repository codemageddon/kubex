from typing import cast

from kubex.api import Api
from kubex.client import create_client
from kubex.core.patch import JsonPatch, MergePatch, StrategicMergePatch
from kubex.k8s.v1_35.apps.v1.deployment import Deployment
from kubex.k8s.v1_35.apps.v1.deployment_spec import DeploymentSpec
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
                    name="example-deploy",
                    labels={"app": "example"},
                ),
                spec=DeploymentSpec(
                    replicas=1,
                    selector=LabelSelector(match_labels={"app": "example"}),
                    template=PodTemplateSpec(
                        metadata=ObjectMetadata(labels={"app": "example"}),
                        spec=PodSpec(
                            containers=[Container(name="nginx", image="nginx:latest")],
                        ),
                    ),
                ),
            ),
        )
        name = cast(str, deployment.metadata.name)

        try:
            # MergePatch — update replicas
            merge_patch = MergePatch(
                Deployment(
                    spec=DeploymentSpec(
                        replicas=3,
                        selector=LabelSelector(match_labels={"app": "example"}),
                        template=PodTemplateSpec(
                            metadata=ObjectMetadata(labels={"app": "example"}),
                            spec=PodSpec(
                                containers=[
                                    Container(name="nginx", image="nginx:latest")
                                ],
                            ),
                        ),
                    )
                )
            )
            patched = await api.patch(name, merge_patch)
            print(
                f"After MergePatch: replicas={patched.spec and patched.spec.replicas}"
            )

            # StrategicMergePatch — add an annotation
            strategic_patch = StrategicMergePatch(
                Deployment(
                    metadata=ObjectMetadata(
                        annotations={"example.com/patched": "true"},
                    )
                )
            )
            patched = await api.patch(name, strategic_patch)
            print(
                f"After StrategicMergePatch: annotations={patched.metadata.annotations}"
            )

            # JsonPatch — add a label
            json_patch = JsonPatch().add("/metadata/labels/version", "v1")
            patched = await api.patch(name, json_patch)
            print(f"After JsonPatch: labels={patched.metadata.labels}")
        finally:
            await api.delete(name)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
