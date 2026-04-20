from __future__ import annotations

from typing import ClassVar, Literal

from pydantic import Field

from kubex.k8s.v1_36.resource.v1beta2.resource_claim_template_spec import (
    ResourceClaimTemplateSpec,
)
from kubex_core.models.interfaces import NamespaceScopedEntity
from kubex_core.models.resource_config import ResourceConfig, Scope


class ResourceClaimTemplate(NamespaceScopedEntity):
    """ResourceClaimTemplate is used to produce ResourceClaim objects. This is an alpha type and requires enabling the DynamicResourceAllocation feature gate."""

    __RESOURCE_CONFIG__: ClassVar[ResourceConfig["ResourceClaimTemplate"]] = (
        ResourceConfig["ResourceClaimTemplate"](
            version="v1beta2",
            kind="ResourceClaimTemplate",
            group="resource.k8s.io",
            plural="resourceclaimtemplates",
            scope=Scope.NAMESPACE,
        )
    )
    api_version: Literal["resource.k8s.io/v1beta2"] = Field(
        default="resource.k8s.io/v1beta2",
        alias="apiVersion",
        description="APIVersion defines the versioned schema of this representation of an object. Servers should convert recognized schemas to the latest internal value, and may reject unrecognized values. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#resources",
    )
    kind: Literal["ResourceClaimTemplate"] = Field(
        default="ResourceClaimTemplate",
        alias="kind",
        description="Kind is a string value representing the REST resource this object represents. Servers may infer this from the endpoint the client submits requests to. Cannot be updated. In CamelCase. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds",
    )
    spec: ResourceClaimTemplateSpec = Field(
        ...,
        alias="spec",
        description="Describes the ResourceClaim that is to be generated. This field is immutable. A ResourceClaim will get created by the control plane for a Pod when needed and then not get updated anymore.",
    )
