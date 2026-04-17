from kubex.k8s.v1_33.apps.v1.deployment_condition import DeploymentCondition
from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class DeploymentStatus(BaseK8sModel):
    """DeploymentStatus is the most recently observed status of the Deployment."""

    available_replicas: int | None = Field(
        default=None,
        alias="availableReplicas",
        description="Total number of available non-terminating pods (ready for at least minReadySeconds) targeted by this deployment.",
    )
    collision_count: int | None = Field(
        default=None,
        alias="collisionCount",
        description="Count of hash collisions for the Deployment. The Deployment controller uses this field as a collision avoidance mechanism when it needs to create the name for the newest ReplicaSet.",
    )
    conditions: list[DeploymentCondition] | None = Field(
        default=None,
        alias="conditions",
        description="Represents the latest available observations of a deployment's current state.",
    )
    observed_generation: int | None = Field(
        default=None,
        alias="observedGeneration",
        description="The generation observed by the deployment controller.",
    )
    ready_replicas: int | None = Field(
        default=None,
        alias="readyReplicas",
        description="Total number of non-terminating pods targeted by this Deployment with a Ready Condition.",
    )
    replicas: int | None = Field(
        default=None,
        alias="replicas",
        description="Total number of non-terminating pods targeted by this deployment (their labels match the selector).",
    )
    terminating_replicas: int | None = Field(
        default=None,
        alias="terminatingReplicas",
        description="Total number of terminating pods targeted by this deployment. Terminating pods have a non-null .metadata.deletionTimestamp and have not yet reached the Failed or Succeeded .status.phase. This is an alpha field. Enable DeploymentReplicaSetTerminatingReplicas to be able to use this field.",
    )
    unavailable_replicas: int | None = Field(
        default=None,
        alias="unavailableReplicas",
        description="Total number of unavailable pods targeted by this deployment. This is the total number of pods that are still required for the deployment to have 100% available capacity. They may either be pods that are running but not yet available or pods that still have not been created.",
    )
    updated_replicas: int | None = Field(
        default=None,
        alias="updatedReplicas",
        description="Total number of non-terminating pods targeted by this deployment that have the desired template spec.",
    )
