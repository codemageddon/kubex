from kubex.k8s.v1_30.apps.v1.deployment_condition import DeploymentCondition
from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class DeploymentStatus(BaseK8sModel):
    """DeploymentStatus is the most recently observed status of the Deployment."""

    available_replicas: int | None = Field(default=None, alias="availableReplicas")
    conditions: list[DeploymentCondition] | None = Field(
        default=None, alias="conditions"
    )
    replicas: int | None = Field(default=None, alias="replicas")
