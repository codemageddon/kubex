from kubex.api import Api, create_api
from kubex.k8s.v1_35.core.v1.container import Container
from kubex.k8s.v1_35.core.v1.pod import Pod
from kubex.k8s.v1_35.core.v1.pod_spec import PodSpec
from kubex_core.models.metadata import ObjectMetadata

NAMESPACE = "default"


async def main() -> None:
    api: Api[Pod] = await create_api(Pod, namespace=NAMESPACE)
    pod = await api.create(
        Pod(
            metadata=ObjectMetadata(generate_name="example-pod-"),
            spec=PodSpec(containers=[Container(name="example", image="nginx")]),
        ),
    )
    assert pod.metadata.name is not None
    print(pod)
    print(await api.metadata.get(pod.metadata.name))
    print(await api.metadata.list())
    await api.delete(pod.metadata.name)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
