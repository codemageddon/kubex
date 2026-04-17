from kubex.k8s.v1_33.core.v1.node_swap_status import NodeSwapStatus
from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class NodeSystemInfo(BaseK8sModel):
    """NodeSystemInfo is a set of ids/uuids to uniquely identify the node."""

    architecture: str = Field(
        ..., alias="architecture", description="The Architecture reported by the node"
    )
    boot_id: str = Field(
        ..., alias="bootID", description="Boot ID reported by the node."
    )
    container_runtime_version: str = Field(
        ...,
        alias="containerRuntimeVersion",
        description="ContainerRuntime Version reported by the node through runtime remote API (e.g. containerd://1.4.2).",
    )
    kernel_version: str = Field(
        ...,
        alias="kernelVersion",
        description="Kernel Version reported by the node from 'uname -r' (e.g. 3.16.0-0.bpo.4-amd64).",
    )
    kube_proxy_version: str = Field(
        ...,
        alias="kubeProxyVersion",
        description="Deprecated: KubeProxy Version reported by the node.",
    )
    kubelet_version: str = Field(
        ..., alias="kubeletVersion", description="Kubelet Version reported by the node."
    )
    machine_id: str = Field(
        ...,
        alias="machineID",
        description="MachineID reported by the node. For unique machine identification in the cluster this field is preferred. Learn more from man(5) machine-id: http://man7.org/linux/man-pages/man5/machine-id.5.html",
    )
    operating_system: str = Field(
        ...,
        alias="operatingSystem",
        description="The Operating System reported by the node",
    )
    os_image: str = Field(
        ...,
        alias="osImage",
        description="OS Image reported by the node from /etc/os-release (e.g. Debian GNU/Linux 7 (wheezy)).",
    )
    swap: NodeSwapStatus | None = Field(
        default=None, alias="swap", description="Swap Info reported by the node."
    )
    system_uuid: str = Field(
        ...,
        alias="systemUUID",
        description="SystemUUID reported by the node. For unique machine identification MachineID is preferred. This field is specific to Red Hat hosts https://access.redhat.com/documentation/en-us/red_hat_subscription_management/1/html/rhsm/uuid",
    )
