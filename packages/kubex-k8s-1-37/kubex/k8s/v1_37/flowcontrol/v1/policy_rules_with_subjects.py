from pydantic import Field

from kubex.k8s.v1_37.flowcontrol.v1.non_resource_policy_rule import (
    NonResourcePolicyRule,
)
from kubex.k8s.v1_37.flowcontrol.v1.resource_policy_rule import ResourcePolicyRule
from kubex.k8s.v1_37.flowcontrol.v1.subject import Subject
from kubex_core.models.base import BaseK8sModel


class PolicyRulesWithSubjects(BaseK8sModel):
    """PolicyRulesWithSubjects prescribes a test that applies to a request to an apiserver. The test considers the subject making the request, the verb being requested, and the resource to be acted upon. This PolicyRulesWithSubjects matches a request if and only if both (a) at least one member of subjects matches the request and (b) at least one member of resourceRules or nonResourceRules matches the request."""

    non_resource_rules: list[NonResourcePolicyRule] | None = Field(
        default=None,
        alias="nonResourceRules",
        description="`nonResourceRules` is a list of NonResourcePolicyRules that identify matching requests according to their verb and the target non-resource URL.",
    )
    resource_rules: list[ResourcePolicyRule] | None = Field(
        default=None,
        alias="resourceRules",
        description="`resourceRules` is a slice of ResourcePolicyRules that identify matching requests according to their verb and the target resource. At least one of `resourceRules` and `nonResourceRules` has to be non-empty.",
    )
    subjects: list[Subject] = Field(
        ...,
        alias="subjects",
        description="subjects is the list of normal user, serviceaccount, or group that this rule cares about. There must be at least one member in this slice. A slice that includes both the system:authenticated and system:unauthenticated user groups matches every request. Required.",
    )
