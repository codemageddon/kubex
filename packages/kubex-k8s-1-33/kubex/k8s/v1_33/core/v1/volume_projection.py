from pydantic import Field

from kubex.k8s.v1_33.core.v1.cluster_trust_bundle_projection import (
    ClusterTrustBundleProjection,
)
from kubex.k8s.v1_33.core.v1.config_map_projection import ConfigMapProjection
from kubex.k8s.v1_33.core.v1.downward_api_projection import DownwardAPIProjection
from kubex.k8s.v1_33.core.v1.secret_projection import SecretProjection
from kubex.k8s.v1_33.core.v1.service_account_token_projection import (
    ServiceAccountTokenProjection,
)
from kubex_core.models.base import BaseK8sModel


class VolumeProjection(BaseK8sModel):
    """Projection that may be projected along with other supported volume types. Exactly one of these fields must be set."""

    cluster_trust_bundle: ClusterTrustBundleProjection | None = Field(
        default=None,
        alias="clusterTrustBundle",
        description="ClusterTrustBundle allows a pod to access the `.spec.trustBundle` field of ClusterTrustBundle objects in an auto-updating file. Alpha, gated by the ClusterTrustBundleProjection feature gate. ClusterTrustBundle objects can either be selected by name, or by the combination of signer name and a label selector. Kubelet performs aggressive normalization of the PEM contents written into the pod filesystem. Esoteric PEM features such as inter-block comments and block headers are stripped. Certificates are deduplicated. The ordering of certificates within the file is arbitrary, and Kubelet may change the order over time.",
    )
    config_map: ConfigMapProjection | None = Field(
        default=None,
        alias="configMap",
        description="configMap information about the configMap data to project",
    )
    downward_api: DownwardAPIProjection | None = Field(
        default=None,
        alias="downwardAPI",
        description="downwardAPI information about the downwardAPI data to project",
    )
    secret: SecretProjection | None = Field(
        default=None,
        alias="secret",
        description="secret information about the secret data to project",
    )
    service_account_token: ServiceAccountTokenProjection | None = Field(
        default=None,
        alias="serviceAccountToken",
        description="serviceAccountToken is information about the serviceAccountToken data to project",
    )
