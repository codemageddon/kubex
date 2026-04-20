from pydantic import Field

from kubex.k8s.v1_34.core.v1.replication_controller_condition import (
    ReplicationControllerCondition,
)
from kubex_core.models.base import BaseK8sModel


class ReplicationControllerStatus(BaseK8sModel):
    """ReplicationControllerStatus represents the current status of a replication controller."""

    available_replicas: int | None = Field(
        default=None,
        alias="availableReplicas",
        description="The number of available replicas (ready for at least minReadySeconds) for this replication controller.",
    )
    conditions: list[ReplicationControllerCondition] | None = Field(
        default=None,
        alias="conditions",
        description="Represents the latest available observations of a replication controller's current state.",
    )
    fully_labeled_replicas: int | None = Field(
        default=None,
        alias="fullyLabeledReplicas",
        description="The number of pods that have labels matching the labels of the pod template of the replication controller.",
    )
    observed_generation: int | None = Field(
        default=None,
        alias="observedGeneration",
        description="ObservedGeneration reflects the generation of the most recently observed replication controller.",
    )
    ready_replicas: int | None = Field(
        default=None,
        alias="readyReplicas",
        description="The number of ready replicas for this replication controller.",
    )
    replicas: int = Field(
        ...,
        alias="replicas",
        description="Replicas is the most recently observed number of replicas. More info: https://kubernetes.io/docs/concepts/workloads/controllers/replicationcontroller#what-is-a-replicationcontroller",
    )
