from kubex.k8s.v1_36.meta.v1.label_selector import LabelSelector
from kubex.k8s.v1_36.networking.v1.network_policy_egress_rule import (
    NetworkPolicyEgressRule,
)
from kubex.k8s.v1_36.networking.v1.network_policy_ingress_rule import (
    NetworkPolicyIngressRule,
)
from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class NetworkPolicySpec(BaseK8sModel):
    """NetworkPolicySpec provides the specification of a NetworkPolicy"""

    egress: list[NetworkPolicyEgressRule] | None = Field(
        default=None,
        alias="egress",
        description="egress is a list of egress rules to be applied to the selected pods. Outgoing traffic is allowed if there are no NetworkPolicies selecting the pod (and cluster policy otherwise allows the traffic), OR if the traffic matches at least one egress rule across all of the NetworkPolicy objects whose podSelector matches the pod. If this field is empty then this NetworkPolicy limits all outgoing traffic (and serves solely to ensure that the pods it selects are isolated by default). This field is beta-level in 1.8",
    )
    ingress: list[NetworkPolicyIngressRule] | None = Field(
        default=None,
        alias="ingress",
        description="ingress is a list of ingress rules to be applied to the selected pods. Traffic is allowed to a pod if there are no NetworkPolicies selecting the pod (and cluster policy otherwise allows the traffic), OR if the traffic source is the pod's local node, OR if the traffic matches at least one ingress rule across all of the NetworkPolicy objects whose podSelector matches the pod. If this field is empty then this NetworkPolicy does not allow any traffic (and serves solely to ensure that the pods it selects are isolated by default)",
    )
    pod_selector: LabelSelector | None = Field(
        default=None,
        alias="podSelector",
        description="podSelector selects the pods to which this NetworkPolicy object applies. The array of rules is applied to any pods selected by this field. An empty selector matches all pods in the policy's namespace. Multiple network policies can select the same set of pods. In this case, the ingress rules for each are combined additively. This field is optional. If it is not specified, it defaults to an empty selector.",
    )
    policy_types: list[str] | None = Field(
        default=None,
        alias="policyTypes",
        description='policyTypes is a list of rule types that the NetworkPolicy relates to. Valid options are ["Ingress"], ["Egress"], or ["Ingress", "Egress"]. If this field is not specified, it will default based on the existence of ingress or egress rules; policies that contain an egress section are assumed to affect egress, and all policies (whether or not they contain an ingress section) are assumed to affect ingress. If you want to write an egress-only policy, you must explicitly specify policyTypes [ "Egress" ]. Likewise, if you want to write a policy that specifies that no egress is allowed, you must specify a policyTypes value that include "Egress" (since such a policy would not include an egress section and would otherwise default to just [ "Ingress" ]). This field is beta-level in 1.8',
    )
