from pydantic import Field

from kubex.k8s.v1_38.core.v1.container_state_running import ContainerStateRunning
from kubex.k8s.v1_38.core.v1.container_state_terminated import ContainerStateTerminated
from kubex.k8s.v1_38.core.v1.container_state_waiting import ContainerStateWaiting
from kubex_core.models.base import BaseK8sModel


class ContainerState(BaseK8sModel):
    """ContainerState holds a possible state of container. Only one of its members may be specified. If none of them is specified, the default one is ContainerStateWaiting."""

    running: ContainerStateRunning | None = Field(
        default=None,
        alias="running",
        description="running is details about a running container",
    )
    terminated: ContainerStateTerminated | None = Field(
        default=None,
        alias="terminated",
        description="terminated is details about a terminated container",
    )
    waiting: ContainerStateWaiting | None = Field(
        default=None,
        alias="waiting",
        description="waiting is details about a waiting container",
    )
