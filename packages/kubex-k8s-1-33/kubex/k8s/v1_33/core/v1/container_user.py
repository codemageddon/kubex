from pydantic import Field

from kubex.k8s.v1_33.core.v1.linux_container_user import LinuxContainerUser
from kubex_core.models.base import BaseK8sModel


class ContainerUser(BaseK8sModel):
    """ContainerUser represents user identity information"""

    linux: LinuxContainerUser | None = Field(
        default=None,
        alias="linux",
        description="Linux holds user identity information initially attached to the first process of the containers in Linux. Note that the actual running identity can be changed if the process has enough privilege to do so.",
    )
