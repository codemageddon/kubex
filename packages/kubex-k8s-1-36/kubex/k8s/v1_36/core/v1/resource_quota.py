from __future__ import annotations

from typing import ClassVar, Literal

from pydantic import Field

from kubex.k8s.v1_36.core.v1.resource_quota_spec import ResourceQuotaSpec
from kubex.k8s.v1_36.core.v1.resource_quota_status import ResourceQuotaStatus
from kubex_core.models.interfaces import HasStatusSubresource, NamespaceScopedEntity
from kubex_core.models.resource_config import ResourceConfig, Scope


class ResourceQuota(NamespaceScopedEntity, HasStatusSubresource):
    """ResourceQuota sets aggregate quota restrictions enforced per namespace"""

    __RESOURCE_CONFIG__: ClassVar[ResourceConfig["ResourceQuota"]] = ResourceConfig[
        "ResourceQuota"
    ](
        version="v1",
        kind="ResourceQuota",
        group="core",
        plural="resourcequotas",
        scope=Scope.NAMESPACE,
    )
    api_version: Literal["v1"] = Field(
        default="v1",
        alias="apiVersion",
        description="APIVersion defines the versioned schema of this representation of an object. Servers should convert recognized schemas to the latest internal value, and may reject unrecognized values. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#resources",
    )
    kind: Literal["ResourceQuota"] = Field(
        default="ResourceQuota",
        alias="kind",
        description="Kind is a string value representing the REST resource this object represents. Servers may infer this from the endpoint the client submits requests to. Cannot be updated. In CamelCase. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds",
    )
    spec: ResourceQuotaSpec | None = Field(
        default=None,
        alias="spec",
        description="Spec defines the desired quota. https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#spec-and-status",
    )
    status: ResourceQuotaStatus | None = Field(
        default=None,
        alias="status",
        description="Status defines the actual enforced quota and its current usage. https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#spec-and-status",
    )
