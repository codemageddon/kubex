from __future__ import annotations

from testcontainers.k3s import K3SContainer  # type: ignore[import-untyped]

from kubex.api import Api
from kubex.k8s.v1_35.core.v1.container import Container
from kubex.k8s.v1_35.core.v1.pod import Pod
from kubex.k8s.v1_35.core.v1.pod_spec import PodSpec
from kubex_core.models.metadata import ObjectMetadata

_BUSYBOX_IMAGE = "busybox:1.36"

_K3S_KUBECONFIG = "/etc/rancher/k3s/k3s.yaml"


def _kubectl(k3s: K3SContainer, *args: str, allow_already_exists: bool = False) -> str:
    result = k3s.get_wrapped_container().exec_run(
        ["kubectl", *args],
        environment={"KUBECONFIG": _K3S_KUBECONFIG},
    )
    output: str = result.output.decode()
    exit_code: int = result.exit_code
    if exit_code != 0:
        if allow_already_exists and "AlreadyExists" in output:
            return output
        raise RuntimeError(
            f"kubectl {' '.join(args)} failed (exit {exit_code}): {output}"
        )
    return output


async def create_busybox_pod(api: Api[Pod], name: str, namespace: str) -> Pod:
    return await api.create(
        Pod(
            metadata=ObjectMetadata(name=name, namespace=namespace),
            spec=PodSpec(
                containers=[
                    Container(
                        name="main",
                        image=_BUSYBOX_IMAGE,
                        command=["sleep", "3600"],
                    )
                ]
            ),
        ),
        namespace=namespace,
    )


async def wait_for_pod_running(
    api: Api[Pod],
    name: str,
    namespace: str,
    *,
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


def mint_sa_token(
    k3s: K3SContainer,
    *,
    sa_name: str = "kubex-test-sa",
    crb_name: str = "kubex-test-sa-binding",
    clusterrole: str = "view",
) -> str:
    _kubectl(
        k3s,
        "create",
        "serviceaccount",
        sa_name,
        "-n",
        "default",
        allow_already_exists=True,
    )
    _kubectl(
        k3s,
        "create",
        "clusterrolebinding",
        crb_name,
        f"--clusterrole={clusterrole}",
        f"--serviceaccount=default:{sa_name}",
        allow_already_exists=True,
    )
    return _kubectl(k3s, "create", "token", sa_name, "-n", "default").strip()
