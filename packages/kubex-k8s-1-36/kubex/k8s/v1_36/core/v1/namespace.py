from __future__ import annotations

from typing import ClassVar, Literal

from pydantic import Field

from kubex.k8s.v1_36.core.v1.namespace_spec import NamespaceSpec
from kubex.k8s.v1_36.core.v1.namespace_status import NamespaceStatus
from kubex_core.models.interfaces import ClusterScopedEntity, HasStatusSubresource
from kubex_core.models.resource_config import ResourceConfig, Scope


class Namespace(ClusterScopedEntity, HasStatusSubresource):
    """Namespace provides a scope for Names. Use of multiple namespaces is optional."""

    __RESOURCE_CONFIG__: ClassVar[ResourceConfig["Namespace"]] = ResourceConfig[
        "Namespace"
    ](
        version="v1",
        kind="Namespace",
        group="core",
        plural="namespaces",
        scope=Scope.CLUSTER,
    )
    api_version: Literal["v1"] = Field(
        default="v1",
        alias="apiVersion",
        description="APIVersion defines the versioned schema of this representation of an object. Servers should convert recognized schemas to the latest internal value, and may reject unrecognized values. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#resources",
    )
    kind: Literal["Namespace"] = Field(
        default="Namespace",
        alias="kind",
        description="Kind is a string value representing the REST resource this object represents. Servers may infer this from the endpoint the client submits requests to. Cannot be updated. In CamelCase. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds",
    )
    spec: NamespaceSpec | None = Field(
        default=None,
        alias="spec",
        description="Spec defines the behavior of the Namespace. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#spec-and-status",
    )
    status: NamespaceStatus | None = Field(
        default=None,
        alias="status",
        description="Status describes the current status of a Namespace. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#spec-and-status",
    )
