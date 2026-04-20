from __future__ import annotations

from typing import ClassVar, Literal

from pydantic import Field

from kubex.k8s.v1_34.authorization.v1.subject_access_review_spec import (
    SubjectAccessReviewSpec,
)
from kubex.k8s.v1_34.authorization.v1.subject_access_review_status import (
    SubjectAccessReviewStatus,
)
from kubex_core.models.interfaces import ClusterScopedEntity
from kubex_core.models.resource_config import ResourceConfig, Scope


class SubjectAccessReview(ClusterScopedEntity):
    """SubjectAccessReview checks whether or not a user or group can perform an action."""

    __RESOURCE_CONFIG__: ClassVar[ResourceConfig["SubjectAccessReview"]] = (
        ResourceConfig["SubjectAccessReview"](
            version="v1",
            kind="SubjectAccessReview",
            group="authorization.k8s.io",
            plural="subjectaccessreviews",
            scope=Scope.CLUSTER,
        )
    )
    api_version: Literal["authorization.k8s.io/v1"] = Field(
        default="authorization.k8s.io/v1",
        alias="apiVersion",
        description="APIVersion defines the versioned schema of this representation of an object. Servers should convert recognized schemas to the latest internal value, and may reject unrecognized values. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#resources",
    )
    kind: Literal["SubjectAccessReview"] = Field(
        default="SubjectAccessReview",
        alias="kind",
        description="Kind is a string value representing the REST resource this object represents. Servers may infer this from the endpoint the client submits requests to. Cannot be updated. In CamelCase. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds",
    )
    spec: SubjectAccessReviewSpec = Field(
        ...,
        alias="spec",
        description="Spec holds information about the request being evaluated",
    )
    status: SubjectAccessReviewStatus | None = Field(
        default=None,
        alias="status",
        description="Status is filled in by the server and indicates whether the request is allowed or not",
    )
