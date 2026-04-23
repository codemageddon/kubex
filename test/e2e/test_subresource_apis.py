from __future__ import annotations

import anyio
import pytest

from kubex.api import Api
from kubex.client import BaseClient
from kubex.core.exceptions import MethodNotAllowed, NotFound
from kubex.core.patch import MergePatch, StrategicMergePatch
from kubex.k8s.v1_35.core.v1.container import Container
from kubex.k8s.v1_35.core.v1.ephemeral_container import EphemeralContainer
from kubex.k8s.v1_35.core.v1.pod import Pod
from kubex.k8s.v1_35.core.v1.pod_spec import PodSpec
from kubex.k8s.v1_35.core.v1.pod_status import PodStatus
from kubex.k8s.v1_35.core.v1.resource_requirements import ResourceRequirements
from kubex_core.models.eviction import Eviction
from kubex_core.models.metadata import ObjectMetadata


async def _create_pod(
    api: Api[Pod], name: str, namespace: str, image: str = "nginx"
) -> Pod:
    return await api.create(
        Pod(
            metadata=ObjectMetadata(name=name, namespace=namespace),
            spec=PodSpec(containers=[Container(name="main", image=image)]),
        ),
        namespace=namespace,
    )


async def _wait_for_phase(
    api: Api[Pod],
    name: str,
    namespace: str,
    phase: str,
    timeout: float = 60.0,
) -> Pod:
    deadline = anyio.current_time() + timeout
    while True:
        pod = await api.get(name, namespace=namespace)
        if pod.status is not None and pod.status.phase == phase:
            return pod
        if anyio.current_time() >= deadline:
            actual = pod.status.phase if pod.status else None
            raise TimeoutError(
                f"Pod {name} did not reach phase {phase} within {timeout}s "
                f"(current: {actual})"
            )
        await anyio.sleep(1)


@pytest.mark.anyio
async def test_status_get(client: BaseClient, tmp_namespace_name: str) -> None:
    api: Api[Pod] = Api(Pod, client=client, namespace=tmp_namespace_name)
    await _create_pod(api, "status-get", tmp_namespace_name)

    result = await api.status.get("status-get")
    assert isinstance(result, Pod)
    assert result.metadata is not None
    assert result.metadata.name == "status-get"
    assert result.status is not None
    assert result.status.phase is not None


@pytest.mark.anyio
async def test_status_replace(client: BaseClient, tmp_namespace_name: str) -> None:
    api: Api[Pod] = Api(Pod, client=client, namespace=tmp_namespace_name)
    await _create_pod(api, "status-replace", tmp_namespace_name)

    pod = await api.status.get("status-replace")
    result = await api.status.replace("status-replace", pod)
    assert isinstance(result, Pod)
    assert result.metadata is not None
    assert result.metadata.name == "status-replace"


@pytest.mark.anyio
async def test_status_patch(client: BaseClient, tmp_namespace_name: str) -> None:
    api: Api[Pod] = Api(Pod, client=client, namespace=tmp_namespace_name)
    await _create_pod(api, "status-patch", tmp_namespace_name)

    patch = MergePatch(
        Pod.model_construct(status=PodStatus(message="patched-by-test"))  # type: ignore[call-arg]
    )
    result = await api.status.patch("status-patch", patch)
    assert isinstance(result, Pod)
    assert result.metadata is not None
    assert result.metadata.name == "status-patch"
    assert result.status is not None
    assert result.status.message == "patched-by-test"


@pytest.mark.anyio
async def test_eviction_create(client: BaseClient, tmp_namespace_name: str) -> None:
    api: Api[Pod] = Api(Pod, client=client, namespace=tmp_namespace_name)
    await _create_pod(api, "eviction-pod", tmp_namespace_name)
    await _wait_for_phase(api, "eviction-pod", tmp_namespace_name, "Running")

    eviction = Eviction(
        metadata=ObjectMetadata(name="eviction-pod", namespace=tmp_namespace_name),
    )
    result = await api.eviction.create("eviction-pod", eviction)
    assert result is not None

    deadline = anyio.current_time() + 30
    while True:
        try:
            pod = await api.get("eviction-pod", namespace=tmp_namespace_name)
            if pod.status is not None and pod.status.phase != "Running":
                break
        except NotFound:
            break
        if anyio.current_time() >= deadline:
            raise TimeoutError("Evicted pod did not stop running within 30s")
        await anyio.sleep(1)


@pytest.mark.anyio
async def test_ephemeral_containers_get(
    client: BaseClient, tmp_namespace_name: str
) -> None:
    api: Api[Pod] = Api(Pod, client=client, namespace=tmp_namespace_name)
    await _create_pod(api, "ec-get", tmp_namespace_name)

    result = await api.ephemeral_containers.get("ec-get")
    assert isinstance(result, Pod)
    assert result.metadata is not None
    assert result.metadata.name == "ec-get"


@pytest.mark.anyio
async def test_ephemeral_containers_patch(
    client: BaseClient, tmp_namespace_name: str
) -> None:
    api: Api[Pod] = Api(Pod, client=client, namespace=tmp_namespace_name)
    await _create_pod(api, "ec-patch", tmp_namespace_name)
    await _wait_for_phase(api, "ec-patch", tmp_namespace_name, "Running")

    patch_body = Pod.model_construct(  # type: ignore[call-arg]
        spec=PodSpec(
            containers=[Container(name="main", image="nginx")],
            ephemeral_containers=[
                EphemeralContainer(
                    name="debugger",
                    image="busybox",
                    command=["sh"],
                ),
            ],
        ),
    )
    patch = StrategicMergePatch(patch_body)
    result = await api.ephemeral_containers.patch("ec-patch", patch)
    assert isinstance(result, Pod)
    assert result.spec is not None
    assert result.spec.ephemeral_containers is not None
    assert len(result.spec.ephemeral_containers) == 1
    assert result.spec.ephemeral_containers[0].name == "debugger"

    get_result = await api.ephemeral_containers.get("ec-patch")
    assert isinstance(get_result, Pod)
    assert get_result.spec is not None
    assert get_result.spec.ephemeral_containers is not None
    assert len(get_result.spec.ephemeral_containers) == 1


@pytest.mark.anyio
async def test_resize_get(client: BaseClient, tmp_namespace_name: str) -> None:
    api: Api[Pod] = Api(Pod, client=client, namespace=tmp_namespace_name)
    await _create_pod(api, "resize-get", tmp_namespace_name)

    try:
        result = await api.resize.get("resize-get")
    except (NotFound, MethodNotAllowed):
        pytest.skip("Resize subresource not supported on this cluster")
    assert isinstance(result, Pod)
    assert result.metadata is not None
    assert result.metadata.name == "resize-get"


@pytest.mark.anyio
async def test_resize_patch(client: BaseClient, tmp_namespace_name: str) -> None:
    api: Api[Pod] = Api(Pod, client=client, namespace=tmp_namespace_name)
    await api.create(
        Pod(
            metadata=ObjectMetadata(name="resize-patch", namespace=tmp_namespace_name),
            spec=PodSpec(
                containers=[
                    Container(
                        name="main",
                        image="nginx",
                        resources=ResourceRequirements(
                            requests={"cpu": "100m", "memory": "64Mi"},
                            limits={"cpu": "100m", "memory": "64Mi"},
                        ),
                    )
                ]
            ),
        ),
        namespace=tmp_namespace_name,
    )

    patch = StrategicMergePatch(
        Pod.model_construct(  # type: ignore[call-arg]
            spec=PodSpec(
                containers=[
                    Container(
                        name="main",
                        resources=ResourceRequirements(
                            requests={"cpu": "200m", "memory": "128Mi"},
                            limits={"cpu": "200m", "memory": "128Mi"},
                        ),
                    )
                ]
            )
        )
    )
    try:
        result = await api.resize.patch("resize-patch", patch)
    except (NotFound, MethodNotAllowed):
        pytest.skip("Resize subresource not supported on this cluster")
    assert isinstance(result, Pod)
    assert result.metadata is not None
    assert result.metadata.name == "resize-patch"
    assert result.spec is not None
    assert result.spec.containers is not None
    main = result.spec.containers[0]
    assert main.resources is not None
    assert main.resources.requests == {"cpu": "200m", "memory": "128Mi"}
    assert main.resources.limits == {"cpu": "200m", "memory": "128Mi"}
