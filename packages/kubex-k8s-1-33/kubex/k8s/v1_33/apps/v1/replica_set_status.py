from pydantic import Field

from kubex.k8s.v1_33.apps.v1.replica_set_condition import ReplicaSetCondition
from kubex_core.models.base import BaseK8sModel


class ReplicaSetStatus(BaseK8sModel):
    """ReplicaSetStatus represents the current status of a ReplicaSet."""

    available_replicas: int | None = Field(
        default=None,
        alias="availableReplicas",
        description="The number of available non-terminating pods (ready for at least minReadySeconds) for this replica set.",
    )
    conditions: list[ReplicaSetCondition] | None = Field(
        default=None,
        alias="conditions",
        description="Represents the latest available observations of a replica set's current state.",
    )
    fully_labeled_replicas: int | None = Field(
        default=None,
        alias="fullyLabeledReplicas",
        description="The number of non-terminating pods that have labels matching the labels of the pod template of the replicaset.",
    )
    observed_generation: int | None = Field(
        default=None,
        alias="observedGeneration",
        description="ObservedGeneration reflects the generation of the most recently observed ReplicaSet.",
    )
    ready_replicas: int | None = Field(
        default=None,
        alias="readyReplicas",
        description="The number of non-terminating pods targeted by this ReplicaSet with a Ready Condition.",
    )
    replicas: int = Field(
        ...,
        alias="replicas",
        description="Replicas is the most recently observed number of non-terminating pods. More info: https://kubernetes.io/docs/concepts/workloads/controllers/replicaset",
    )
    terminating_replicas: int | None = Field(
        default=None,
        alias="terminatingReplicas",
        description="The number of terminating pods for this replica set. Terminating pods have a non-null .metadata.deletionTimestamp and have not yet reached the Failed or Succeeded .status.phase. This is an alpha field. Enable DeploymentReplicaSetTerminatingReplicas to be able to use this field.",
    )
