from kubex.k8s.v1_34.meta.v1.label_selector import LabelSelector
from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class PodAffinityTerm(BaseK8sModel):
    """Defines a set of pods (namely those matching the labelSelector relative to the given namespace(s)) that this pod should be co-located (affinity) or not co-located (anti-affinity) with, where co-located is defined as running on a node whose value of the label with key <topologyKey> matches that of any node on which a pod of the set of pods is running"""

    label_selector: LabelSelector | None = Field(
        default=None,
        alias="labelSelector",
        description="A label query over a set of resources, in this case pods. If it's null, this PodAffinityTerm matches with no Pods.",
    )
    match_label_keys: list[str] | None = Field(
        default=None,
        alias="matchLabelKeys",
        description="MatchLabelKeys is a set of pod label keys to select which pods will be taken into consideration. The keys are used to lookup values from the incoming pod labels, those key-value labels are merged with `labelSelector` as `key in (value)` to select the group of existing pods which pods will be taken into consideration for the incoming pod's pod (anti) affinity. Keys that don't exist in the incoming pod labels will be ignored. The default value is empty. The same key is forbidden to exist in both matchLabelKeys and labelSelector. Also, matchLabelKeys cannot be set when labelSelector isn't set.",
    )
    mismatch_label_keys: list[str] | None = Field(
        default=None,
        alias="mismatchLabelKeys",
        description="MismatchLabelKeys is a set of pod label keys to select which pods will be taken into consideration. The keys are used to lookup values from the incoming pod labels, those key-value labels are merged with `labelSelector` as `key notin (value)` to select the group of existing pods which pods will be taken into consideration for the incoming pod's pod (anti) affinity. Keys that don't exist in the incoming pod labels will be ignored. The default value is empty. The same key is forbidden to exist in both mismatchLabelKeys and labelSelector. Also, mismatchLabelKeys cannot be set when labelSelector isn't set.",
    )
    namespace_selector: LabelSelector | None = Field(
        default=None,
        alias="namespaceSelector",
        description='A label query over the set of namespaces that the term applies to. The term is applied to the union of the namespaces selected by this field and the ones listed in the namespaces field. null selector and null or empty namespaces list means "this pod\'s namespace". An empty selector ({}) matches all namespaces.',
    )
    namespaces: list[str] | None = Field(
        default=None,
        alias="namespaces",
        description='namespaces specifies a static list of namespace names that the term applies to. The term is applied to the union of the namespaces listed in this field and the ones selected by namespaceSelector. null or empty namespaces list and null namespaceSelector means "this pod\'s namespace".',
    )
    topology_key: str = Field(
        ...,
        alias="topologyKey",
        description="This pod should be co-located (affinity) or not co-located (anti-affinity) with the pods matching the labelSelector in the specified namespaces, where co-located is defined as running on a node whose value of the label with key topologyKey matches that of any node on which any of the selected pods is running. Empty topologyKey is not allowed.",
    )
