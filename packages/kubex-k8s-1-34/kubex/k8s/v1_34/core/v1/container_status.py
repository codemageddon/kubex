from pydantic import Field

from kubex.k8s.v1_34.core.v1.container_state import ContainerState
from kubex.k8s.v1_34.core.v1.container_user import ContainerUser
from kubex.k8s.v1_34.core.v1.resource_requirements import ResourceRequirements
from kubex.k8s.v1_34.core.v1.resource_status import ResourceStatus
from kubex.k8s.v1_34.core.v1.volume_mount_status import VolumeMountStatus
from kubex_core.models.base import BaseK8sModel


class ContainerStatus(BaseK8sModel):
    """ContainerStatus contains details for the current status of this container."""

    allocated_resources: dict[str, str] | None = Field(
        default=None,
        alias="allocatedResources",
        description="AllocatedResources represents the compute resources allocated for this container by the node. Kubelet sets this value to Container.Resources.Requests upon successful pod admission and after successfully admitting desired pod resize.",
    )
    allocated_resources_status: list[ResourceStatus] | None = Field(
        default=None,
        alias="allocatedResourcesStatus",
        description="AllocatedResourcesStatus represents the status of various resources allocated for this Pod.",
    )
    container_id: str | None = Field(
        default=None,
        alias="containerID",
        description="ContainerID is the ID of the container in the format '<type>://<container_id>'. Where type is a container runtime identifier, returned from Version call of CRI API (for example \"containerd\").",
    )
    image: str = Field(
        ...,
        alias="image",
        description="Image is the name of container image that the container is running. The container image may not match the image used in the PodSpec, as it may have been resolved by the runtime. More info: https://kubernetes.io/docs/concepts/containers/images.",
    )
    image_id: str = Field(
        ...,
        alias="imageID",
        description="ImageID is the image ID of the container's image. The image ID may not match the image ID of the image used in the PodSpec, as it may have been resolved by the runtime.",
    )
    last_state: ContainerState | None = Field(
        default=None,
        alias="lastState",
        description="LastTerminationState holds the last termination state of the container to help debug container crashes and restarts. This field is not populated if the container is still running and RestartCount is 0.",
    )
    name: str = Field(
        ...,
        alias="name",
        description="Name is a DNS_LABEL representing the unique name of the container. Each container in a pod must have a unique name across all container types. Cannot be updated.",
    )
    ready: bool = Field(
        ...,
        alias="ready",
        description="Ready specifies whether the container is currently passing its readiness check. The value will change as readiness probes keep executing. If no readiness probes are specified, this field defaults to true once the container is fully started (see Started field). The value is typically used to determine whether a container is ready to accept traffic.",
    )
    resources: ResourceRequirements | None = Field(
        default=None,
        alias="resources",
        description="Resources represents the compute resource requests and limits that have been successfully enacted on the running container after it has been started or has been successfully resized.",
    )
    restart_count: int = Field(
        ...,
        alias="restartCount",
        description="RestartCount holds the number of times the container has been restarted. Kubelet makes an effort to always increment the value, but there are cases when the state may be lost due to node restarts and then the value may be reset to 0. The value is never negative.",
    )
    started: bool | None = Field(
        default=None,
        alias="started",
        description="Started indicates whether the container has finished its postStart lifecycle hook and passed its startup probe. Initialized as false, becomes true after startupProbe is considered successful. Resets to false when the container is restarted, or if kubelet loses state temporarily. In both cases, startup probes will run again. Is always true when no startupProbe is defined and container is running and has passed the postStart lifecycle hook. The null value must be treated the same as false.",
    )
    state: ContainerState | None = Field(
        default=None,
        alias="state",
        description="State holds details about the container's current condition.",
    )
    stop_signal: str | None = Field(
        default=None,
        alias="stopSignal",
        description="StopSignal reports the effective stop signal for this container",
    )
    user: ContainerUser | None = Field(
        default=None,
        alias="user",
        description="User represents user identity information initially attached to the first process of the container",
    )
    volume_mounts: list[VolumeMountStatus] | None = Field(
        default=None, alias="volumeMounts", description="Status of volume mounts."
    )
