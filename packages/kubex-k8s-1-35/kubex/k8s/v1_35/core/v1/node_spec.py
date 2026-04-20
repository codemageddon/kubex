from pydantic import Field

from kubex.k8s.v1_35.core.v1.node_config_source import NodeConfigSource
from kubex.k8s.v1_35.core.v1.taint import Taint
from kubex_core.models.base import BaseK8sModel


class NodeSpec(BaseK8sModel):
    """NodeSpec describes the attributes that a node is created with."""

    config_source: NodeConfigSource | None = Field(
        default=None,
        alias="configSource",
        description="Deprecated: Previously used to specify the source of the node's configuration for the DynamicKubeletConfig feature. This feature is removed.",
    )
    external_id: str | None = Field(
        default=None,
        alias="externalID",
        description="Deprecated. Not all kubelets will set this field. Remove field after 1.13. see: https://issues.k8s.io/61966",
    )
    pod_cidr: str | None = Field(
        default=None,
        alias="podCIDR",
        description="PodCIDR represents the pod IP range assigned to the node.",
    )
    pod_cidrs: list[str] | None = Field(
        default=None,
        alias="podCIDRs",
        description="podCIDRs represents the IP ranges assigned to the node for usage by Pods on that node. If this field is specified, the 0th entry must match the podCIDR field. It may contain at most 1 value for each of IPv4 and IPv6.",
    )
    provider_id: str | None = Field(
        default=None,
        alias="providerID",
        description="ID of the node assigned by the cloud provider in the format: <ProviderName>://<ProviderSpecificNodeID>",
    )
    taints: list[Taint] | None = Field(
        default=None, alias="taints", description="If specified, the node's taints."
    )
    unschedulable: bool | None = Field(
        default=None,
        alias="unschedulable",
        description="Unschedulable controls node schedulability of new pods. By default, node is schedulable. More info: https://kubernetes.io/docs/concepts/nodes/node/#manual-node-administration",
    )
