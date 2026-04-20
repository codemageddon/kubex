from pydantic import Field

from kubex.k8s.v1_37.apps.v1.stateful_set_condition import StatefulSetCondition
from kubex_core.models.base import BaseK8sModel


class StatefulSetStatus(BaseK8sModel):
    """StatefulSetStatus represents the current state of a StatefulSet."""

    available_replicas: int | None = Field(
        default=None,
        alias="availableReplicas",
        description="Total number of available pods (ready for at least minReadySeconds) targeted by this statefulset.",
    )
    collision_count: int | None = Field(
        default=None,
        alias="collisionCount",
        description="collisionCount is the count of hash collisions for the StatefulSet. The StatefulSet controller uses this field as a collision avoidance mechanism when it needs to create the name for the newest ControllerRevision.",
    )
    conditions: list[StatefulSetCondition] | None = Field(
        default=None,
        alias="conditions",
        description="Represents the latest available observations of a statefulset's current state.",
    )
    current_replicas: int | None = Field(
        default=None,
        alias="currentReplicas",
        description="currentReplicas is the number of Pods created by the StatefulSet controller from the StatefulSet version indicated by currentRevision.",
    )
    current_revision: str | None = Field(
        default=None,
        alias="currentRevision",
        description="currentRevision, if not empty, indicates the version of the StatefulSet used to generate Pods in the sequence [0,currentReplicas).",
    )
    observed_generation: int | None = Field(
        default=None,
        alias="observedGeneration",
        description="observedGeneration is the most recent generation observed for this StatefulSet. It corresponds to the StatefulSet's generation, which is updated on mutation by the API Server.",
    )
    ready_replicas: int | None = Field(
        default=None,
        alias="readyReplicas",
        description="readyReplicas is the number of pods created for this StatefulSet with a Ready Condition.",
    )
    replicas: int = Field(
        ...,
        alias="replicas",
        description="replicas is the number of Pods created by the StatefulSet controller.",
    )
    update_revision: str | None = Field(
        default=None,
        alias="updateRevision",
        description="updateRevision, if not empty, indicates the version of the StatefulSet used to generate Pods in the sequence [replicas-updatedReplicas,replicas)",
    )
    updated_replicas: int | None = Field(
        default=None,
        alias="updatedReplicas",
        description="updatedReplicas is the number of Pods created by the StatefulSet controller from the StatefulSet version indicated by updateRevision.",
    )
