from kubex.k8s.v1_34.batch.v1.pod_failure_policy_rule import PodFailurePolicyRule
from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class PodFailurePolicy(BaseK8sModel):
    """PodFailurePolicy describes how failed pods influence the backoffLimit."""

    rules: list[PodFailurePolicyRule] = Field(
        ...,
        alias="rules",
        description="A list of pod failure policy rules. The rules are evaluated in order. Once a rule matches a Pod failure, the remaining of the rules are ignored. When no rule matches the Pod failure, the default handling applies - the counter of pod failures is incremented and it is checked against the backoffLimit. At most 20 elements are allowed.",
    )
