from enum import Enum

from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class DeploymentConditionType(str, Enum):
    AVAILABLE = "Available"
    PROGRESSING = "Progressing"
    REPLICA_FAILURE = "ReplicaFailure"


class DeploymentCondition(BaseK8sModel):
    """DeploymentCondition describes a condition of a Deployment."""

    reason: str | None = Field(default=None, alias="reason")
    status: str = Field(..., alias="status")
    type_: DeploymentConditionType = Field(
        ..., alias="type", description="Type of deployment condition."
    )
