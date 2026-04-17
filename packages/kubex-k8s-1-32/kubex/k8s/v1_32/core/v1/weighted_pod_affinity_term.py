from kubex.k8s.v1_32.core.v1.pod_affinity_term import PodAffinityTerm
from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class WeightedPodAffinityTerm(BaseK8sModel):
    """The weights of all of the matched WeightedPodAffinityTerm fields are added per-node to find the most preferred node(s)"""

    pod_affinity_term: PodAffinityTerm = Field(
        ...,
        alias="podAffinityTerm",
        description="Required. A pod affinity term, associated with the corresponding weight.",
    )
    weight: int = Field(
        ...,
        alias="weight",
        description="weight associated with matching the corresponding podAffinityTerm, in the range 1-100.",
    )
