from kubex.k8s.v1_36.meta.v1.label_selector import LabelSelector
from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class AggregationRule(BaseK8sModel):
    """AggregationRule describes how to locate ClusterRoles to aggregate into the ClusterRole"""

    cluster_role_selectors: list[LabelSelector] | None = Field(
        default=None,
        alias="clusterRoleSelectors",
        description="ClusterRoleSelectors holds a list of selectors which will be used to find ClusterRoles and create the rules. If any of the selectors match, then the ClusterRole's permissions will be added",
    )
