from pydantic import Field

from kubex.k8s.v1_38.apps.v1.deployment_condition import DeploymentCondition
from kubex_core.models.base import BaseK8sModel


class DeploymentStatus(BaseK8sModel):
    """DeploymentStatus is the most recently observed status of the Deployment."""

    available_replicas: int | None = Field(
        default=None,
        alias="availableReplicas",
        description="availableReplicas is the total number of available non-terminating pods (ready for at least minReadySeconds) targeted by this deployment.",
    )
    collision_count: int | None = Field(
        default=None,
        alias="collisionCount",
        description="collisionCount is the number of hash collisions for the Deployment. The Deployment controller uses this field as a collision avoidance mechanism when it needs to create the name for the newest ReplicaSet.",
    )
    conditions: list[DeploymentCondition] | None = Field(
        default=None,
        alias="conditions",
        description="conditions lists the latest available observations of a deployment's current state.",
    )
    observed_generation: int | None = Field(
        default=None,
        alias="observedGeneration",
        description="observedGeneration is the generation observed by the deployment controller.",
    )
    ready_replicas: int | None = Field(
        default=None,
        alias="readyReplicas",
        description="readyReplicas is the total number of non-terminating pods targeted by this Deployment with a Ready Condition.",
    )
    replicas: int | None = Field(
        default=None,
        alias="replicas",
        description="replicas is the total number of non-terminating pods targeted by this deployment (their labels match the selector).",
    )
    terminating_replicas: int | None = Field(
        default=None,
        alias="terminatingReplicas",
        description="terminatingReplicas is the number of terminating pods targeted by this deployment. Terminating pods have a non-null .metadata.deletionTimestamp and have not yet reached the Failed or Succeeded .status.phase. This is a beta field and requires enabling DeploymentReplicaSetTerminatingReplicas feature (enabled by default).",
    )
    unavailable_replicas: int | None = Field(
        default=None,
        alias="unavailableReplicas",
        description="unavailableReplicas is the total number of unavailable pods targeted by this deployment. This is the total number of pods that are still required for the deployment to have 100% available capacity. They may either be pods that are running but not yet available or pods that still have not been created.",
    )
    updated_replicas: int | None = Field(
        default=None,
        alias="updatedReplicas",
        description="updatedReplicas is total number of non-terminating pods targeted by this deployment that have the desired template spec.",
    )
