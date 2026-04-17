from __future__ import annotations

from typing import ClassVar, Literal

from kubex.k8s.v1_32.apiextensions_k8s_io.v1.custom_resource_definition_spec import (
    CustomResourceDefinitionSpec,
)
from kubex.k8s.v1_32.apiextensions_k8s_io.v1.custom_resource_definition_status import (
    CustomResourceDefinitionStatus,
)
from kubex_core.models.interfaces import ClusterScopedEntity, HasStatusSubresource
from kubex_core.models.resource_config import ResourceConfig, Scope
from pydantic import Field


class CustomResourceDefinition(ClusterScopedEntity, HasStatusSubresource):
    """CustomResourceDefinition represents a resource that should be exposed on the API server. Its name MUST be in the format <.spec.name>.<.spec.group>."""

    __RESOURCE_CONFIG__: ClassVar[ResourceConfig["CustomResourceDefinition"]] = (
        ResourceConfig["CustomResourceDefinition"](
            version="v1",
            kind="CustomResourceDefinition",
            group="apiextensions.k8s.io",
            plural="customresourcedefinitions",
            scope=Scope.CLUSTER,
        )
    )
    api_version: Literal["apiextensions.k8s.io/v1"] = Field(
        default="apiextensions.k8s.io/v1",
        alias="apiVersion",
        description="APIVersion defines the versioned schema of this representation of an object. Servers should convert recognized schemas to the latest internal value, and may reject unrecognized values. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#resources",
    )
    kind: Literal["CustomResourceDefinition"] = Field(
        default="CustomResourceDefinition",
        alias="kind",
        description="Kind is a string value representing the REST resource this object represents. Servers may infer this from the endpoint the client submits requests to. Cannot be updated. In CamelCase. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds",
    )
    spec: CustomResourceDefinitionSpec = Field(
        ...,
        alias="spec",
        description="spec describes how the user wants the resources to appear",
    )
    status: CustomResourceDefinitionStatus | None = Field(
        default=None,
        alias="status",
        description="status indicates the actual state of the CustomResourceDefinition",
    )
