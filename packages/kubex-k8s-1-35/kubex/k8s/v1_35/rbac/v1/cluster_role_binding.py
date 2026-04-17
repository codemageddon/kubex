from __future__ import annotations

from typing import ClassVar, Literal

from kubex.k8s.v1_35.rbac.v1.role_ref import RoleRef
from kubex.k8s.v1_35.rbac.v1.subject import Subject
from kubex_core.models.interfaces import ClusterScopedEntity
from kubex_core.models.resource_config import ResourceConfig, Scope
from pydantic import Field


class ClusterRoleBinding(ClusterScopedEntity):
    """ClusterRoleBinding references a ClusterRole, but not contain it. It can reference a ClusterRole in the global namespace, and adds who information via Subject."""

    __RESOURCE_CONFIG__: ClassVar[ResourceConfig["ClusterRoleBinding"]] = (
        ResourceConfig["ClusterRoleBinding"](
            version="v1",
            kind="ClusterRoleBinding",
            group="rbac.authorization.k8s.io",
            plural="clusterrolebindings",
            scope=Scope.CLUSTER,
        )
    )
    api_version: Literal["rbac.authorization.k8s.io/v1"] = Field(
        default="rbac.authorization.k8s.io/v1",
        alias="apiVersion",
        description="APIVersion defines the versioned schema of this representation of an object. Servers should convert recognized schemas to the latest internal value, and may reject unrecognized values. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#resources",
    )
    kind: Literal["ClusterRoleBinding"] = Field(
        default="ClusterRoleBinding",
        alias="kind",
        description="Kind is a string value representing the REST resource this object represents. Servers may infer this from the endpoint the client submits requests to. Cannot be updated. In CamelCase. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds",
    )
    role_ref: RoleRef = Field(
        ...,
        alias="roleRef",
        description="RoleRef can only reference a ClusterRole in the global namespace. If the RoleRef cannot be resolved, the Authorizer must return an error. This field is immutable.",
    )
    subjects: list[Subject] | None = Field(
        default=None,
        alias="subjects",
        description="Subjects holds references to the objects the role applies to.",
    )
