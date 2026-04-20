from pydantic import Field

from kubex.k8s.v1_30._common import IntOrString
from kubex_core.models.base import BaseK8sModel


class DeploymentSpec(BaseK8sModel):
    """DeploymentSpec is the specification of the desired behavior of the Deployment."""

    max_surge: IntOrString | None = Field(default=None, alias="maxSurge")
    min_ready_seconds: int | None = Field(default=None, alias="minReadySeconds")
    paused: bool | None = Field(default=None, alias="paused")
    replicas: int | None = Field(default=None, alias="replicas")
