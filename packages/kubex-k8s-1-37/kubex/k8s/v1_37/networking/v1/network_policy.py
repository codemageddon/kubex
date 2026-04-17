from __future__ import annotations

from typing import ClassVar, Literal

from kubex.k8s.v1_37.networking.v1.network_policy_spec import NetworkPolicySpec
from kubex_core.models.interfaces import NamespaceScopedEntity
from kubex_core.models.resource_config import ResourceConfig, Scope
from pydantic import Field


class NetworkPolicy(NamespaceScopedEntity):
    """NetworkPolicy describes what network traffic is allowed for a set of Pods"""

    __RESOURCE_CONFIG__: ClassVar[ResourceConfig["NetworkPolicy"]] = ResourceConfig[
        "NetworkPolicy"
    ](
        version="v1",
        kind="NetworkPolicy",
        group="networking.k8s.io",
        plural="networkpolicies",
        scope=Scope.NAMESPACE,
    )
    api_version: Literal["networking.k8s.io/v1"] = Field(
        default="networking.k8s.io/v1",
        alias="apiVersion",
        description="APIVersion defines the versioned schema of this representation of an object. Servers should convert recognized schemas to the latest internal value, and may reject unrecognized values. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#resources",
    )
    kind: Literal["NetworkPolicy"] = Field(
        default="NetworkPolicy",
        alias="kind",
        description="Kind is a string value representing the REST resource this object represents. Servers may infer this from the endpoint the client submits requests to. Cannot be updated. In CamelCase. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds",
    )
    spec: NetworkPolicySpec | None = Field(
        default=None,
        alias="spec",
        description="spec represents the specification of the desired behavior for this NetworkPolicy.",
    )
