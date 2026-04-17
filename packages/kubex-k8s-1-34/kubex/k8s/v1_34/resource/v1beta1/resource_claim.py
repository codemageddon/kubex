from __future__ import annotations

from typing import ClassVar, Literal

from kubex.k8s.v1_34.resource.v1beta1.resource_claim_spec import ResourceClaimSpec
from kubex.k8s.v1_34.resource.v1beta1.resource_claim_status import ResourceClaimStatus
from kubex_core.models.interfaces import HasStatusSubresource, NamespaceScopedEntity
from kubex_core.models.resource_config import ResourceConfig, Scope
from pydantic import Field


class ResourceClaim(NamespaceScopedEntity, HasStatusSubresource):
    """ResourceClaim describes a request for access to resources in the cluster, for use by workloads. For example, if a workload needs an accelerator device with specific properties, this is how that request is expressed. The status stanza tracks whether this claim has been satisfied and what specific resources have been allocated. This is an alpha type and requires enabling the DynamicResourceAllocation feature gate."""

    __RESOURCE_CONFIG__: ClassVar[ResourceConfig["ResourceClaim"]] = ResourceConfig[
        "ResourceClaim"
    ](
        version="v1beta1",
        kind="ResourceClaim",
        group="resource.k8s.io",
        plural="resourceclaims",
        scope=Scope.NAMESPACE,
    )
    api_version: Literal["resource.k8s.io/v1beta1"] = Field(
        default="resource.k8s.io/v1beta1",
        alias="apiVersion",
        description="APIVersion defines the versioned schema of this representation of an object. Servers should convert recognized schemas to the latest internal value, and may reject unrecognized values. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#resources",
    )
    kind: Literal["ResourceClaim"] = Field(
        default="ResourceClaim",
        alias="kind",
        description="Kind is a string value representing the REST resource this object represents. Servers may infer this from the endpoint the client submits requests to. Cannot be updated. In CamelCase. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds",
    )
    spec: ResourceClaimSpec = Field(
        ...,
        alias="spec",
        description="Spec describes what is being requested and how to configure it. The spec is immutable.",
    )
    status: ResourceClaimStatus | None = Field(
        default=None,
        alias="status",
        description="Status describes whether the claim is ready to use and what has been allocated.",
    )
