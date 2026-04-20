from pydantic import Field

from kubex.k8s.v1_37.networking.v1.network_policy_peer import NetworkPolicyPeer
from kubex.k8s.v1_37.networking.v1.network_policy_port import NetworkPolicyPort
from kubex_core.models.base import BaseK8sModel


class NetworkPolicyEgressRule(BaseK8sModel):
    """NetworkPolicyEgressRule describes a particular set of traffic that is allowed out of pods matched by a NetworkPolicySpec's podSelector. The traffic must match both ports and to. This type is beta-level in 1.8"""

    ports: list[NetworkPolicyPort] | None = Field(
        default=None,
        alias="ports",
        description="ports is a list of destination ports for outgoing traffic. Each item in this list is combined using a logical OR. If this field is empty or missing, this rule matches all ports (traffic not restricted by port). If this field is present and contains at least one item, then this rule allows traffic only if the traffic matches at least one port in the list.",
    )
    to: list[NetworkPolicyPeer] | None = Field(
        default=None,
        alias="to",
        description="to is a list of destinations for outgoing traffic of pods selected for this rule. Items in this list are combined using a logical OR operation. If this field is empty or missing, this rule matches all destinations (traffic not restricted by destination). If this field is present and contains at least one item, this rule allows traffic only if the traffic matches at least one item in the to list.",
    )
