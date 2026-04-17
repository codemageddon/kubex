from __future__ import annotations

from typing import ClassVar, Literal

from kubex.k8s.v1_32.networking.v1.ingress_class_spec import IngressClassSpec
from kubex_core.models.interfaces import ClusterScopedEntity
from kubex_core.models.resource_config import ResourceConfig, Scope
from pydantic import Field


class IngressClass(ClusterScopedEntity):
    """IngressClass represents the class of the Ingress, referenced by the Ingress Spec. The `ingressclass.kubernetes.io/is-default-class` annotation can be used to indicate that an IngressClass should be considered default. When a single IngressClass resource has this annotation set to true, new Ingress resources without a class specified will be assigned this default class."""

    __RESOURCE_CONFIG__: ClassVar[ResourceConfig["IngressClass"]] = ResourceConfig[
        "IngressClass"
    ](
        version="v1",
        kind="IngressClass",
        group="networking.k8s.io",
        plural="ingressclasses",
        scope=Scope.CLUSTER,
    )
    api_version: Literal["networking.k8s.io/v1"] = Field(
        default="networking.k8s.io/v1",
        alias="apiVersion",
        description="APIVersion defines the versioned schema of this representation of an object. Servers should convert recognized schemas to the latest internal value, and may reject unrecognized values. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#resources",
    )
    kind: Literal["IngressClass"] = Field(
        default="IngressClass",
        alias="kind",
        description="Kind is a string value representing the REST resource this object represents. Servers may infer this from the endpoint the client submits requests to. Cannot be updated. In CamelCase. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds",
    )
    spec: IngressClassSpec | None = Field(
        default=None,
        alias="spec",
        description="spec is the desired state of the IngressClass. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#spec-and-status",
    )
