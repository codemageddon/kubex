from pydantic import Field

from kubex.k8s.v1_37.batch.v1.success_policy_rule import SuccessPolicyRule
from kubex_core.models.base import BaseK8sModel


class SuccessPolicy(BaseK8sModel):
    """SuccessPolicy describes when a Job can be declared as succeeded based on the success of some indexes."""

    rules: list[SuccessPolicyRule] = Field(
        ...,
        alias="rules",
        description='rules represents the list of alternative rules for the declaring the Jobs as successful before `.status.succeeded >= .spec.completions`. Once any of the rules are met, the "SuccessCriteriaMet" condition is added, and the lingering pods are removed. The terminal state for such a Job has the "Complete" condition. Additionally, these rules are evaluated in order; Once the Job meets one of the rules, other rules are ignored. At most 20 elements are allowed.',
    )
