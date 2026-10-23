from pydantic import Field

from kubex.k8s.v1_38.apps.v1.replica_set_condition import ReplicaSetCondition
from kubex_core.models.base import BaseK8sModel


class ReplicaSetStatus(BaseK8sModel):
    """ReplicaSetStatus represents the current status of a ReplicaSet."""

    available_replicas: int | None = Field(
        default=None,
        alias="availableReplicas",
        description="availableReplicas is the number of available non-terminating pods (ready for at least minReadySeconds) for this ReplicaSet.",
    )
    conditions: list[ReplicaSetCondition] | None = Field(
        default=None,
        alias="conditions",
        description="conditions lists the latest available observations of a ReplicaSet's current state.",
    )
    fully_labeled_replicas: int | None = Field(
        default=None,
        alias="fullyLabeledReplicas",
        description="fullyLabeledReplicas is the number of non-terminating pods that have labels matching the labels of the pod template of the ReplicaSet.",
    )
    observed_generation: int | None = Field(
        default=None,
        alias="observedGeneration",
        description="observedGeneration reflects the generation of the most recently observed ReplicaSet.",
    )
    ready_replicas: int | None = Field(
        default=None,
        alias="readyReplicas",
        description="readyReplicas is the number of non-terminating pods targeted by this ReplicaSet with a Ready Condition.",
    )
    replicas: int = Field(
        ...,
        alias="replicas",
        description="replicas is the most recently observed number of non-terminating pods. More info: https://kubernetes.io/docs/concepts/workloads/controllers/replicaset",
    )
    terminating_replicas: int | None = Field(
        default=None,
        alias="terminatingReplicas",
        description="terminatingReplicas is the number of terminating pods for this ReplicaSet. Terminating pods have a non-null .metadata.deletionTimestamp and have not yet reached the Failed or Succeeded .status.phase. This is a beta field and requires enabling DeploymentReplicaSetTerminatingReplicas feature (enabled by default).",
    )
