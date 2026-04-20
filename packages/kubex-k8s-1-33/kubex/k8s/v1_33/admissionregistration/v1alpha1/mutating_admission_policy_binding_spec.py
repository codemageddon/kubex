from pydantic import Field

from kubex.k8s.v1_33.admissionregistration.v1alpha1.match_resources import (
    MatchResources,
)
from kubex.k8s.v1_33.admissionregistration.v1alpha1.param_ref import ParamRef
from kubex_core.models.base import BaseK8sModel


class MutatingAdmissionPolicyBindingSpec(BaseK8sModel):
    """MutatingAdmissionPolicyBindingSpec is the specification of the MutatingAdmissionPolicyBinding."""

    match_resources: MatchResources | None = Field(
        default=None,
        alias="matchResources",
        description="matchResources limits what resources match this binding and may be mutated by it. Note that if matchResources matches a resource, the resource must also match a policy's matchConstraints and matchConditions before the resource may be mutated. When matchResources is unset, it does not constrain resource matching, and only the policy's matchConstraints and matchConditions must match for the resource to be mutated. Additionally, matchResources.resourceRules are optional and do not constraint matching when unset. Note that this is differs from MutatingAdmissionPolicy matchConstraints, where resourceRules are required. The CREATE, UPDATE and CONNECT operations are allowed. The DELETE operation may not be matched. '*' matches CREATE, UPDATE and CONNECT.",
    )
    param_ref: ParamRef | None = Field(
        default=None,
        alias="paramRef",
        description="paramRef specifies the parameter resource used to configure the admission control policy. It should point to a resource of the type specified in spec.ParamKind of the bound MutatingAdmissionPolicy. If the policy specifies a ParamKind and the resource referred to by ParamRef does not exist, this binding is considered mis-configured and the FailurePolicy of the MutatingAdmissionPolicy applied. If the policy does not specify a ParamKind then this field is ignored, and the rules are evaluated without a param.",
    )
    policy_name: str | None = Field(
        default=None,
        alias="policyName",
        description="policyName references a MutatingAdmissionPolicy name which the MutatingAdmissionPolicyBinding binds to. If the referenced resource does not exist, this binding is considered invalid and will be ignored Required.",
    )
