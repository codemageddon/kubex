from __future__ import annotations

from typing import ClassVar, Literal

from kubex.k8s.v1_34.apiregistration.v1.api_service_spec import APIServiceSpec
from kubex.k8s.v1_34.apiregistration.v1.api_service_status import APIServiceStatus
from kubex_core.models.interfaces import ClusterScopedEntity, HasStatusSubresource
from kubex_core.models.resource_config import ResourceConfig, Scope
from pydantic import Field


class APIService(ClusterScopedEntity, HasStatusSubresource):
    """APIService represents a server for a particular GroupVersion. Name must be "version.group"."""

    __RESOURCE_CONFIG__: ClassVar[ResourceConfig["APIService"]] = ResourceConfig[
        "APIService"
    ](
        version="v1",
        kind="APIService",
        group="apiregistration.k8s.io",
        plural="apiservices",
        scope=Scope.CLUSTER,
    )
    api_version: Literal["apiregistration.k8s.io/v1"] = Field(
        default="apiregistration.k8s.io/v1",
        alias="apiVersion",
        description="APIVersion defines the versioned schema of this representation of an object. Servers should convert recognized schemas to the latest internal value, and may reject unrecognized values. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#resources",
    )
    kind: Literal["APIService"] = Field(
        default="APIService",
        alias="kind",
        description="Kind is a string value representing the REST resource this object represents. Servers may infer this from the endpoint the client submits requests to. Cannot be updated. In CamelCase. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds",
    )
    spec: APIServiceSpec | None = Field(
        default=None,
        alias="spec",
        description="Spec contains information for locating and communicating with a server",
    )
    status: APIServiceStatus | None = Field(
        default=None,
        alias="status",
        description="Status contains derived information about an API server",
    )
