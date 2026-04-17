from __future__ import annotations

from typing import ClassVar, Literal

from kubex.k8s.v1_32.authentication.v1.self_subject_review_status import (
    SelfSubjectReviewStatus,
)
from kubex_core.models.interfaces import ClusterScopedEntity
from kubex_core.models.resource_config import ResourceConfig, Scope
from pydantic import Field


class SelfSubjectReview(ClusterScopedEntity):
    """SelfSubjectReview contains the user information that the kube-apiserver has about the user making this request. When using impersonation, users will receive the user info of the user being impersonated. If impersonation or request header authentication is used, any extra keys will have their case ignored and returned as lowercase."""

    __RESOURCE_CONFIG__: ClassVar[ResourceConfig["SelfSubjectReview"]] = ResourceConfig[
        "SelfSubjectReview"
    ](
        version="v1",
        kind="SelfSubjectReview",
        group="authentication.k8s.io",
        plural="selfsubjectreviews",
        scope=Scope.CLUSTER,
    )
    api_version: Literal["authentication.k8s.io/v1"] = Field(
        default="authentication.k8s.io/v1",
        alias="apiVersion",
        description="APIVersion defines the versioned schema of this representation of an object. Servers should convert recognized schemas to the latest internal value, and may reject unrecognized values. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#resources",
    )
    kind: Literal["SelfSubjectReview"] = Field(
        default="SelfSubjectReview",
        alias="kind",
        description="Kind is a string value representing the REST resource this object represents. Servers may infer this from the endpoint the client submits requests to. Cannot be updated. In CamelCase. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds",
    )
    status: SelfSubjectReviewStatus | None = Field(
        default=None,
        alias="status",
        description="Status is filled in by the server with the user attributes.",
    )
