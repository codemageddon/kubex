from kubex.k8s.v1_33.apps.v1.daemon_set_condition import DaemonSetCondition
from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class DaemonSetStatus(BaseK8sModel):
    """DaemonSetStatus represents the current status of a daemon set."""

    collision_count: int | None = Field(
        default=None,
        alias="collisionCount",
        description="Count of hash collisions for the DaemonSet. The DaemonSet controller uses this field as a collision avoidance mechanism when it needs to create the name for the newest ControllerRevision.",
    )
    conditions: list[DaemonSetCondition] | None = Field(
        default=None,
        alias="conditions",
        description="Represents the latest available observations of a DaemonSet's current state.",
    )
    current_number_scheduled: int = Field(
        ...,
        alias="currentNumberScheduled",
        description="The number of nodes that are running at least 1 daemon pod and are supposed to run the daemon pod. More info: https://kubernetes.io/docs/concepts/workloads/controllers/daemonset/",
    )
    desired_number_scheduled: int = Field(
        ...,
        alias="desiredNumberScheduled",
        description="The total number of nodes that should be running the daemon pod (including nodes correctly running the daemon pod). More info: https://kubernetes.io/docs/concepts/workloads/controllers/daemonset/",
    )
    number_available: int | None = Field(
        default=None,
        alias="numberAvailable",
        description="The number of nodes that should be running the daemon pod and have one or more of the daemon pod running and available (ready for at least spec.minReadySeconds)",
    )
    number_misscheduled: int = Field(
        ...,
        alias="numberMisscheduled",
        description="The number of nodes that are running the daemon pod, but are not supposed to run the daemon pod. More info: https://kubernetes.io/docs/concepts/workloads/controllers/daemonset/",
    )
    number_ready: int = Field(
        ...,
        alias="numberReady",
        description="numberReady is the number of nodes that should be running the daemon pod and have one or more of the daemon pod running with a Ready Condition.",
    )
    number_unavailable: int | None = Field(
        default=None,
        alias="numberUnavailable",
        description="The number of nodes that should be running the daemon pod and have none of the daemon pod running and available (ready for at least spec.minReadySeconds)",
    )
    observed_generation: int | None = Field(
        default=None,
        alias="observedGeneration",
        description="The most recent generation observed by the daemon set controller.",
    )
    updated_number_scheduled: int | None = Field(
        default=None,
        alias="updatedNumberScheduled",
        description="The total number of nodes that are running updated daemon pod",
    )
