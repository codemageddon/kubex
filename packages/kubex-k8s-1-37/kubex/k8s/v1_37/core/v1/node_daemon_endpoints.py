from pydantic import Field

from kubex.k8s.v1_37.core.v1.daemon_endpoint import DaemonEndpoint
from kubex_core.models.base import BaseK8sModel


class NodeDaemonEndpoints(BaseK8sModel):
    """NodeDaemonEndpoints lists ports opened by daemons running on the Node."""

    kubelet_endpoint: DaemonEndpoint | None = Field(
        default=None,
        alias="kubeletEndpoint",
        description="Endpoint on which Kubelet is listening.",
    )
