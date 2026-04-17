from __future__ import annotations

from typing import ClassVar, Literal

from kubex.k8s.v1_33.rbac.v1.aggregation_rule import AggregationRule
from kubex.k8s.v1_33.rbac.v1.policy_rule import PolicyRule
from kubex_core.models.interfaces import ClusterScopedEntity
from kubex_core.models.resource_config import ResourceConfig, Scope
from pydantic import Field


class ClusterRole(ClusterScopedEntity):
    """ClusterRole is a cluster level, logical grouping of PolicyRules that can be referenced as a unit by a RoleBinding or ClusterRoleBinding."""

    __RESOURCE_CONFIG__: ClassVar[ResourceConfig["ClusterRole"]] = ResourceConfig[
        "ClusterRole"
    ](
        version="v1",
        kind="ClusterRole",
        group="rbac.authorization.k8s.io",
        plural="clusterroles",
        scope=Scope.CLUSTER,
    )
    aggregation_rule: AggregationRule | None = Field(
        default=None,
        alias="aggregationRule",
        description="AggregationRule is an optional field that describes how to build the Rules for this ClusterRole. If AggregationRule is set, then the Rules are controller managed and direct changes to Rules will be stomped by the controller.",
    )
    api_version: Literal["rbac.authorization.k8s.io/v1"] = Field(
        default="rbac.authorization.k8s.io/v1",
        alias="apiVersion",
        description="APIVersion defines the versioned schema of this representation of an object. Servers should convert recognized schemas to the latest internal value, and may reject unrecognized values. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#resources",
    )
    kind: Literal["ClusterRole"] = Field(
        default="ClusterRole",
        alias="kind",
        description="Kind is a string value representing the REST resource this object represents. Servers may infer this from the endpoint the client submits requests to. Cannot be updated. In CamelCase. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds",
    )
    rules: list[PolicyRule] | None = Field(
        default=None,
        alias="rules",
        description="Rules holds all the PolicyRules for this ClusterRole",
    )
