from __future__ import annotations

from typing import ClassVar, Literal

from kubex.k8s.v1_37.authorization.v1.self_subject_access_review_spec import (
    SelfSubjectAccessReviewSpec,
)
from kubex.k8s.v1_37.authorization.v1.subject_access_review_status import (
    SubjectAccessReviewStatus,
)
from kubex_core.models.interfaces import ClusterScopedEntity
from kubex_core.models.resource_config import ResourceConfig, Scope
from pydantic import Field


class SelfSubjectAccessReview(ClusterScopedEntity):
    """SelfSubjectAccessReview checks whether or the current user can perform an action. Not filling in a spec.namespace means "in all namespaces". Self is a special case, because users should always be able to check whether they can perform an action"""

    __RESOURCE_CONFIG__: ClassVar[ResourceConfig["SelfSubjectAccessReview"]] = (
        ResourceConfig["SelfSubjectAccessReview"](
            version="v1",
            kind="SelfSubjectAccessReview",
            group="authorization.k8s.io",
            plural="selfsubjectaccessreviews",
            scope=Scope.CLUSTER,
        )
    )
    api_version: Literal["authorization.k8s.io/v1"] = Field(
        default="authorization.k8s.io/v1",
        alias="apiVersion",
        description="APIVersion defines the versioned schema of this representation of an object. Servers should convert recognized schemas to the latest internal value, and may reject unrecognized values. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#resources",
    )
    kind: Literal["SelfSubjectAccessReview"] = Field(
        default="SelfSubjectAccessReview",
        alias="kind",
        description="Kind is a string value representing the REST resource this object represents. Servers may infer this from the endpoint the client submits requests to. Cannot be updated. In CamelCase. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds",
    )
    spec: SelfSubjectAccessReviewSpec = Field(
        ...,
        alias="spec",
        description="spec holds information about the request being evaluated. user and groups must be empty",
    )
    status: SubjectAccessReviewStatus | None = Field(
        default=None,
        alias="status",
        description="status is filled in by the server and indicates whether the request is allowed or not",
    )
