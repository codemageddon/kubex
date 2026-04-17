from __future__ import annotations

from typing import ClassVar, Literal

from kubex.k8s.v1_37.resource.v1alpha3.resource_pool_status_request_spec import (
    ResourcePoolStatusRequestSpec,
)
from kubex.k8s.v1_37.resource.v1alpha3.resource_pool_status_request_status import (
    ResourcePoolStatusRequestStatus,
)
from kubex_core.models.interfaces import ClusterScopedEntity, HasStatusSubresource
from kubex_core.models.resource_config import ResourceConfig, Scope
from pydantic import Field


class ResourcePoolStatusRequest(ClusterScopedEntity, HasStatusSubresource):
    """ResourcePoolStatusRequest triggers a one-time calculation of resource pool status based on the provided filters. Once status is set, the request is considered complete and will not be reprocessed. Users should delete and recreate requests to get updated information."""

    __RESOURCE_CONFIG__: ClassVar[ResourceConfig["ResourcePoolStatusRequest"]] = (
        ResourceConfig["ResourcePoolStatusRequest"](
            version="v1alpha3",
            kind="ResourcePoolStatusRequest",
            group="resource.k8s.io",
            plural="resourcepoolstatusrequests",
            scope=Scope.CLUSTER,
        )
    )
    api_version: Literal["resource.k8s.io/v1alpha3"] = Field(
        default="resource.k8s.io/v1alpha3",
        alias="apiVersion",
        description="APIVersion defines the versioned schema of this representation of an object. Servers should convert recognized schemas to the latest internal value, and may reject unrecognized values. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#resources",
    )
    kind: Literal["ResourcePoolStatusRequest"] = Field(
        default="ResourcePoolStatusRequest",
        alias="kind",
        description="Kind is a string value representing the REST resource this object represents. Servers may infer this from the endpoint the client submits requests to. Cannot be updated. In CamelCase. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds",
    )
    spec: ResourcePoolStatusRequestSpec = Field(
        ...,
        alias="spec",
        description="Spec defines the filters for which pools to include in the status. The spec is immutable once created.",
    )
    status: ResourcePoolStatusRequestStatus | None = Field(
        default=None,
        alias="status",
        description="Status is populated by the controller with the calculated pool status. When status is non-nil, the request is considered complete and the entire object becomes immutable.",
    )
