from __future__ import annotations

from typing import ClassVar, Literal

from pydantic import Field

from kubex.k8s.v1_32.core.v1.object_reference import ObjectReference
from kubex_core.models.interfaces import NamespaceScopedEntity
from kubex_core.models.resource_config import ResourceConfig, Scope


class Binding(NamespaceScopedEntity):
    """Binding ties one object to another; for example, a pod is bound to a node by a scheduler."""

    __RESOURCE_CONFIG__: ClassVar[ResourceConfig["Binding"]] = ResourceConfig[
        "Binding"
    ](
        version="v1",
        kind="Binding",
        group="core",
        plural="bindings",
        scope=Scope.NAMESPACE,
    )
    api_version: Literal["v1"] = Field(
        default="v1",
        alias="apiVersion",
        description="APIVersion defines the versioned schema of this representation of an object. Servers should convert recognized schemas to the latest internal value, and may reject unrecognized values. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#resources",
    )
    kind: Literal["Binding"] = Field(
        default="Binding",
        alias="kind",
        description="Kind is a string value representing the REST resource this object represents. Servers may infer this from the endpoint the client submits requests to. Cannot be updated. In CamelCase. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds",
    )
    target: ObjectReference = Field(
        ...,
        alias="target",
        description="The target object that you want to bind to the standard object.",
    )
