from pydantic import Field

from kubex_core.models.base import BaseK8sModel


class WorkloadReference(BaseK8sModel):
    """WorkloadReference identifies the Workload object and PodGroup membership that a Pod belongs to. The scheduler uses this information to apply workload-aware scheduling semantics."""

    name: str = Field(
        ...,
        alias="name",
        description="Name defines the name of the Workload object this Pod belongs to. Workload must be in the same namespace as the Pod. If it doesn't match any existing Workload, the Pod will remain unschedulable until a Workload object is created and observed by the kube-scheduler. It must be a DNS subdomain.",
    )
    pod_group: str = Field(
        ...,
        alias="podGroup",
        description="PodGroup is the name of the PodGroup within the Workload that this Pod belongs to. If it doesn't match any existing PodGroup within the Workload, the Pod will remain unschedulable until the Workload object is recreated and observed by the kube-scheduler. It must be a DNS label.",
    )
    pod_group_replica_key: str | None = Field(
        default=None,
        alias="podGroupReplicaKey",
        description="PodGroupReplicaKey specifies the replica key of the PodGroup to which this Pod belongs. It is used to distinguish pods belonging to different replicas of the same pod group. The pod group policy is applied separately to each replica. When set, it must be a DNS label.",
    )
