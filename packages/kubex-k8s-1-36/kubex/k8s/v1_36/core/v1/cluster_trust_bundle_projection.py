from kubex.k8s.v1_36.meta.v1.label_selector import LabelSelector
from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class ClusterTrustBundleProjection(BaseK8sModel):
    """ClusterTrustBundleProjection describes how to select a set of ClusterTrustBundle objects and project their contents into the pod filesystem."""

    label_selector: LabelSelector | None = Field(
        default=None,
        alias="labelSelector",
        description='Select all ClusterTrustBundles that match this label selector. Only has effect if signerName is set. Mutually-exclusive with name. If unset, interpreted as "match nothing". If set but empty, interpreted as "match everything".',
    )
    name: str | None = Field(
        default=None,
        alias="name",
        description="Select a single ClusterTrustBundle by object name. Mutually-exclusive with signerName and labelSelector.",
    )
    optional: bool | None = Field(
        default=None,
        alias="optional",
        description="If true, don't block pod startup if the referenced ClusterTrustBundle(s) aren't available. If using name, then the named ClusterTrustBundle is allowed not to exist. If using signerName, then the combination of signerName and labelSelector is allowed to match zero ClusterTrustBundles.",
    )
    path: str = Field(
        ...,
        alias="path",
        description="Relative path from the volume root to write the bundle.",
    )
    signer_name: str | None = Field(
        default=None,
        alias="signerName",
        description="Select all ClusterTrustBundles that match this signer name. Mutually-exclusive with name. The contents of all selected ClusterTrustBundles will be unified and deduplicated.",
    )
