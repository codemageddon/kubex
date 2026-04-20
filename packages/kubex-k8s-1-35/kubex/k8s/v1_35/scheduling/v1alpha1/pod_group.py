from pydantic import Field

from kubex.k8s.v1_35.scheduling.v1alpha1.pod_group_policy import PodGroupPolicy
from kubex_core.models.base import BaseK8sModel


class PodGroup(BaseK8sModel):
    """PodGroup represents a set of pods with a common scheduling policy."""

    name: str = Field(
        ...,
        alias="name",
        description="Name is a unique identifier for the PodGroup within the Workload. It must be a DNS label. This field is immutable.",
    )
    policy: PodGroupPolicy = Field(
        ...,
        alias="policy",
        description="Policy defines the scheduling policy for this PodGroup.",
    )
