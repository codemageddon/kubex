"""Shared helpers to prepare a K3s testcontainer + seed pods for a run.

Used by both the pytest `conftest.py` (for pytest-benchmark-based wall-time
measurement) and the standalone `benchmarks.run` orchestrator (for memory +
CPU runs). Keeping this in a non-test module lets the standalone script
bring up a cluster without importing pytest.
"""

from __future__ import annotations

import asyncio
import tempfile
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from yaml import safe_load

from kubex.api.api import Api, create_api
from kubex.client.httpx import HttpxClient
from kubex.configuration.configuration import KubeConfig
from kubex.configuration.file_config import configure_from_kubeconfig
from kubex.k8s.v1_33.core.v1.container import Container
from kubex.k8s.v1_33.core.v1.namespace import Namespace
from kubex.k8s.v1_33.core.v1.pod import Pod
from kubex.k8s.v1_33.core.v1.pod_spec import PodSpec
from kubex_core.models.metadata import ObjectMetadata

# K3s image pinned to 1.33 so the wire server matches the kubernetes-asyncio
# 33.x client schema and the kubex-k8s-1-33 model package.
DEFAULT_K3S_IMAGE = "rancher/k3s:v1.33.4-k3s1"


def k8s_version_from_image(image: str = DEFAULT_K3S_IMAGE) -> str:
    """Extract the Kubernetes version (e.g. '1.33.4') from a K3s image tag."""
    tag = image.split(":")[-1].lstrip("v")  # 'v1.33.4-k3s1' -> '1.33.4-k3s1'
    return tag.split("-k3s")[0]  # '1.33.4-k3s1' -> '1.33.4'


# Pause image — minimal container used for seeded pods. We do not wait for
# Running state; list/get endpoints serve the created object regardless of
# container status.
PAUSE_IMAGE = "registry.k8s.io/pause:3.9"
BUSYBOX_IMAGE = "busybox:1.36"


@asynccontextmanager
async def k3s_cluster(image: str = DEFAULT_K3S_IMAGE) -> AsyncIterator[str]:
    """Start a K3s testcontainer and yield a kubeconfig path.

    Uses the existing testcontainers wrapper already in the repo's dev deps.
    """
    from testcontainers.k3s import K3SContainer  # type: ignore[import-untyped]

    container = K3SContainer(image=image, enable_cgroup_mount=False)
    container.start()
    try:
        kube_path = Path(
            tempfile.mkstemp(prefix="bench-kubeconfig-", suffix=".yaml")[1]
        )
        kube_path.write_text(container.config_yaml())
        try:
            yield str(kube_path)
        finally:
            kube_path.unlink(missing_ok=True)
    finally:
        container.stop()


async def _kubex_client(kubeconfig_path: str) -> HttpxClient:
    kube_cfg = KubeConfig.model_validate(safe_load(Path(kubeconfig_path).read_text()))
    client_cfg = await configure_from_kubeconfig(kube_cfg)
    client = HttpxClient(client_cfg)
    await client.__aenter__()
    return client


async def seed_namespace(
    kubeconfig_path: str,
    n_pods: int,
    log_pod_name: str = "log-emitter",
    seeded_prefix: str = "seed-",
) -> str:
    """Create a namespace, seed `n_pods` pause pods, and spawn one log emitter.

    Returns the namespace name. Creation is done in batches to keep the
    control-plane happy while still being fast. Pod creation is awaited only
    to the 201 response; we do not wait for container Running.
    """
    client = await _kubex_client(kubeconfig_path)
    try:
        namespace_api: Api[Namespace] = await create_api(Namespace, client=client)
        ns_name = f"bench-{uuid.uuid4().hex[:10]}"
        await namespace_api.create(
            Namespace(metadata=ObjectMetadata(name=ns_name)),
        )

        pod_api: Api[Pod] = await create_api(Pod, client=client)

        async def _mk(i: int) -> None:
            pod = Pod(
                metadata=ObjectMetadata(name=f"{seeded_prefix}{i}", namespace=ns_name),
                spec=PodSpec(containers=[Container(name="c", image=PAUSE_IMAGE)]),
            )
            await pod_api.create(pod, namespace=ns_name)

        # Batch of 20 concurrent creates; adjust if K3s chokes.
        batch = 20
        for start in range(0, n_pods, batch):
            await asyncio.gather(
                *(_mk(i) for i in range(start, min(start + batch, n_pods)))
            )

        emitter = Pod(
            metadata=ObjectMetadata(name=log_pod_name, namespace=ns_name),
            spec=PodSpec(
                containers=[
                    Container(
                        name="c",
                        image=BUSYBOX_IMAGE,
                        command=[
                            "sh",
                            "-c",
                            "i=0; while true; do echo line-$i; i=$((i+1)); "
                            "sleep 0.001; done",
                        ],
                    )
                ]
            ),
        )
        await pod_api.create(emitter, namespace=ns_name)
        return ns_name
    finally:
        await client.__aexit__(None, None, None)


async def teardown_namespace(kubeconfig_path: str, namespace: str) -> None:
    client = await _kubex_client(kubeconfig_path)
    try:
        namespace_api: Api[Namespace] = await create_api(Namespace, client=client)
        try:
            await namespace_api.delete(namespace, grace_period_seconds=0)
        except Exception:
            pass
    finally:
        await client.__aexit__(None, None, None)
