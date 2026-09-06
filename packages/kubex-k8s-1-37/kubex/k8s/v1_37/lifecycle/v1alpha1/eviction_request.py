from __future__ import annotations

from typing import ClassVar, Literal

from pydantic import Field

from kubex.k8s.v1_37.lifecycle.v1alpha1.eviction_request_spec import EvictionRequestSpec
from kubex.k8s.v1_37.lifecycle.v1alpha1.eviction_request_status import (
    EvictionRequestStatus,
)
from kubex_core.models.interfaces import HasStatusSubresource, NamespaceScopedEntity
from kubex_core.models.resource_config import ResourceConfig, Scope


class EvictionRequest(NamespaceScopedEntity, HasStatusSubresource):
    """EvictionRequest defines a request that should ideally result in a graceful eviction of a .spec.target (e.g. termination of a pod). The evictionrequest-controller observes intents of all EvictionRequests and transforms them into Evictions. - .spec.requester is set as a label on the Eviction for easier lookup. - Each target can have a set of responders assigned to it. Eviction objects are observed by these responders, who implement the eviction logic and update the Eviction's status with progress. There is many-to-many relationship between EvictionRequests and Evictions in general. And many-to-one if the target is a pod. If all requesters withdraw their eviction intent for a common target, the eviction will be canceled. Deleting an EvictionRequest also counts as a withdrawal. Once all EvictionRequest of a target are removed, the corresponding Evictions are eventually garbage collected."""

    __RESOURCE_CONFIG__: ClassVar[ResourceConfig["EvictionRequest"]] = ResourceConfig[
        "EvictionRequest"
    ](
        version="v1alpha1",
        kind="EvictionRequest",
        group="lifecycle.k8s.io",
        plural="evictionrequests",
        scope=Scope.NAMESPACE,
    )
    api_version: Literal["lifecycle.k8s.io/v1alpha1"] = Field(
        default="lifecycle.k8s.io/v1alpha1",
        alias="apiVersion",
        description="APIVersion defines the versioned schema of this representation of an object. Servers should convert recognized schemas to the latest internal value, and may reject unrecognized values. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#resources",
    )
    kind: Literal["EvictionRequest"] = Field(
        default="EvictionRequest",
        alias="kind",
        description="Kind is a string value representing the REST resource this object represents. Servers may infer this from the endpoint the client submits requests to. Cannot be updated. In CamelCase. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds",
    )
    spec: EvictionRequestSpec = Field(
        ...,
        alias="spec",
        description="spec defines the eviction request specification. https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#spec-and-status",
    )
    status: EvictionRequestStatus | None = Field(
        default=None,
        alias="status",
        description="status represents the most recently observed status of the eviction request. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#spec-and-status",
    )
