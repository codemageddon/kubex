from pydantic import Field

from kubex.k8s.v1_33.apps.v1.rolling_update_deployment import RollingUpdateDeployment
from kubex_core.models.base import BaseK8sModel


class DeploymentStrategy(BaseK8sModel):
    """DeploymentStrategy describes how to replace existing pods with new ones."""

    rolling_update: RollingUpdateDeployment | None = Field(
        default=None,
        alias="rollingUpdate",
        description="Rolling update config params. Present only if DeploymentStrategyType = RollingUpdate.",
    )
    type_: str | None = Field(
        default=None,
        alias="type",
        description='Type of deployment. Can be "Recreate" or "RollingUpdate". Default is RollingUpdate.',
    )
