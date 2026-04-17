from __future__ import annotations

from typing import ClassVar, Literal

from kubex.k8s.v1_35.rbac.v1.policy_rule import PolicyRule
from kubex_core.models.interfaces import NamespaceScopedEntity
from kubex_core.models.resource_config import ResourceConfig, Scope
from pydantic import Field


class Role(NamespaceScopedEntity):
    """Role is a namespaced, logical grouping of PolicyRules that can be referenced as a unit by a RoleBinding."""

    __RESOURCE_CONFIG__: ClassVar[ResourceConfig["Role"]] = ResourceConfig["Role"](
        version="v1",
        kind="Role",
        group="rbac.authorization.k8s.io",
        plural="roles",
        scope=Scope.NAMESPACE,
    )
    api_version: Literal["rbac.authorization.k8s.io/v1"] = Field(
        default="rbac.authorization.k8s.io/v1",
        alias="apiVersion",
        description="APIVersion defines the versioned schema of this representation of an object. Servers should convert recognized schemas to the latest internal value, and may reject unrecognized values. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#resources",
    )
    kind: Literal["Role"] = Field(
        default="Role",
        alias="kind",
        description="Kind is a string value representing the REST resource this object represents. Servers may infer this from the endpoint the client submits requests to. Cannot be updated. In CamelCase. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds",
    )
    rules: list[PolicyRule] | None = Field(
        default=None,
        alias="rules",
        description="Rules holds all the PolicyRules for this Role",
    )
