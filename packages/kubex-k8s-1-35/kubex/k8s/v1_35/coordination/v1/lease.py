from __future__ import annotations

from typing import ClassVar, Literal

from pydantic import Field

from kubex.k8s.v1_35.coordination.v1.lease_spec import LeaseSpec
from kubex_core.models.interfaces import NamespaceScopedEntity
from kubex_core.models.resource_config import ResourceConfig, Scope


class Lease(NamespaceScopedEntity):
    """Lease defines a lease concept."""

    __RESOURCE_CONFIG__: ClassVar[ResourceConfig["Lease"]] = ResourceConfig["Lease"](
        version="v1",
        kind="Lease",
        group="coordination.k8s.io",
        plural="leases",
        scope=Scope.NAMESPACE,
    )
    api_version: Literal["coordination.k8s.io/v1"] = Field(
        default="coordination.k8s.io/v1",
        alias="apiVersion",
        description="APIVersion defines the versioned schema of this representation of an object. Servers should convert recognized schemas to the latest internal value, and may reject unrecognized values. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#resources",
    )
    kind: Literal["Lease"] = Field(
        default="Lease",
        alias="kind",
        description="Kind is a string value representing the REST resource this object represents. Servers may infer this from the endpoint the client submits requests to. Cannot be updated. In CamelCase. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds",
    )
    spec: LeaseSpec | None = Field(
        default=None,
        alias="spec",
        description="spec contains the specification of the Lease. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#spec-and-status",
    )
