from pydantic import Field

from kubex.k8s.v1_36.core.v1.node_affinity import NodeAffinity
from kubex.k8s.v1_36.core.v1.pod_affinity import PodAffinity
from kubex.k8s.v1_36.core.v1.pod_anti_affinity import PodAntiAffinity
from kubex_core.models.base import BaseK8sModel


class Affinity(BaseK8sModel):
    """Affinity is a group of affinity scheduling rules."""

    node_affinity: NodeAffinity | None = Field(
        default=None,
        alias="nodeAffinity",
        description="Describes node affinity scheduling rules for the pod.",
    )
    pod_affinity: PodAffinity | None = Field(
        default=None,
        alias="podAffinity",
        description="Describes pod affinity scheduling rules (e.g. co-locate this pod in the same node, zone, etc. as some other pod(s)).",
    )
    pod_anti_affinity: PodAntiAffinity | None = Field(
        default=None,
        alias="podAntiAffinity",
        description="Describes pod anti-affinity scheduling rules (e.g. avoid putting this pod in the same node, zone, etc. as some other pod(s)).",
    )
