from __future__ import annotations

from typing import ClassVar, Literal

from pydantic import Field

from kubex.k8s.v1_32.apiserverinternal.v1alpha1.storage_version_spec import (
    StorageVersionSpec,
)
from kubex.k8s.v1_32.apiserverinternal.v1alpha1.storage_version_status import (
    StorageVersionStatus,
)
from kubex_core.models.interfaces import ClusterScopedEntity, HasStatusSubresource
from kubex_core.models.resource_config import ResourceConfig, Scope


class StorageVersion(ClusterScopedEntity, HasStatusSubresource):
    """Storage version of a specific resource."""

    __RESOURCE_CONFIG__: ClassVar[ResourceConfig["StorageVersion"]] = ResourceConfig[
        "StorageVersion"
    ](
        version="v1alpha1",
        kind="StorageVersion",
        group="internal.apiserver.k8s.io",
        plural="storageversions",
        scope=Scope.CLUSTER,
    )
    api_version: Literal["internal.apiserver.k8s.io/v1alpha1"] = Field(
        default="internal.apiserver.k8s.io/v1alpha1",
        alias="apiVersion",
        description="APIVersion defines the versioned schema of this representation of an object. Servers should convert recognized schemas to the latest internal value, and may reject unrecognized values. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#resources",
    )
    kind: Literal["StorageVersion"] = Field(
        default="StorageVersion",
        alias="kind",
        description="Kind is a string value representing the REST resource this object represents. Servers may infer this from the endpoint the client submits requests to. Cannot be updated. In CamelCase. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds",
    )
    spec: StorageVersionSpec = Field(
        ...,
        alias="spec",
        description="Spec is an empty spec. It is here to comply with Kubernetes API style.",
    )
    status: StorageVersionStatus = Field(
        ...,
        alias="status",
        description="API server instances report the version they can decode and the version they encode objects to when persisting objects in the backend.",
    )
