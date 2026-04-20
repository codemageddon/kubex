from __future__ import annotations

from typing import ClassVar, Literal

from pydantic import Field

from kubex.k8s.v1_36.certificates.v1beta1.cluster_trust_bundle_spec import (
    ClusterTrustBundleSpec,
)
from kubex_core.models.interfaces import ClusterScopedEntity
from kubex_core.models.resource_config import ResourceConfig, Scope


class ClusterTrustBundle(ClusterScopedEntity):
    """ClusterTrustBundle is a cluster-scoped container for X.509 trust anchors (root certificates). ClusterTrustBundle objects are considered to be readable by any authenticated user in the cluster, because they can be mounted by pods using the `clusterTrustBundle` projection. All service accounts have read access to ClusterTrustBundles by default. Users who only have namespace-level access to a cluster can read ClusterTrustBundles by impersonating a serviceaccount that they have access to. It can be optionally associated with a particular assigner, in which case it contains one valid set of trust anchors for that signer. Signers may have multiple associated ClusterTrustBundles; each is an independent set of trust anchors for that signer. Admission control is used to enforce that only users with permissions on the signer can create or modify the corresponding bundle."""

    __RESOURCE_CONFIG__: ClassVar[ResourceConfig["ClusterTrustBundle"]] = (
        ResourceConfig["ClusterTrustBundle"](
            version="v1beta1",
            kind="ClusterTrustBundle",
            group="certificates.k8s.io",
            plural="clustertrustbundles",
            scope=Scope.CLUSTER,
        )
    )
    api_version: Literal["certificates.k8s.io/v1beta1"] = Field(
        default="certificates.k8s.io/v1beta1",
        alias="apiVersion",
        description="APIVersion defines the versioned schema of this representation of an object. Servers should convert recognized schemas to the latest internal value, and may reject unrecognized values. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#resources",
    )
    kind: Literal["ClusterTrustBundle"] = Field(
        default="ClusterTrustBundle",
        alias="kind",
        description="Kind is a string value representing the REST resource this object represents. Servers may infer this from the endpoint the client submits requests to. Cannot be updated. In CamelCase. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds",
    )
    spec: ClusterTrustBundleSpec = Field(
        ...,
        alias="spec",
        description="spec contains the signer (if any) and trust anchors.",
    )
