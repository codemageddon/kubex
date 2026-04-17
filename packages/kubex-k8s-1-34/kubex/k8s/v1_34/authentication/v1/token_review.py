from __future__ import annotations

from typing import ClassVar, Literal

from kubex.k8s.v1_34.authentication.v1.token_review_spec import TokenReviewSpec
from kubex.k8s.v1_34.authentication.v1.token_review_status import TokenReviewStatus
from kubex_core.models.interfaces import ClusterScopedEntity
from kubex_core.models.resource_config import ResourceConfig, Scope
from pydantic import Field


class TokenReview(ClusterScopedEntity):
    """TokenReview attempts to authenticate a token to a known user. Note: TokenReview requests may be cached by the webhook token authenticator plugin in the kube-apiserver."""

    __RESOURCE_CONFIG__: ClassVar[ResourceConfig["TokenReview"]] = ResourceConfig[
        "TokenReview"
    ](
        version="v1",
        kind="TokenReview",
        group="authentication.k8s.io",
        plural="tokenreviews",
        scope=Scope.CLUSTER,
    )
    api_version: Literal["authentication.k8s.io/v1"] = Field(
        default="authentication.k8s.io/v1",
        alias="apiVersion",
        description="APIVersion defines the versioned schema of this representation of an object. Servers should convert recognized schemas to the latest internal value, and may reject unrecognized values. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#resources",
    )
    kind: Literal["TokenReview"] = Field(
        default="TokenReview",
        alias="kind",
        description="Kind is a string value representing the REST resource this object represents. Servers may infer this from the endpoint the client submits requests to. Cannot be updated. In CamelCase. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds",
    )
    spec: TokenReviewSpec = Field(
        ...,
        alias="spec",
        description="Spec holds information about the request being evaluated",
    )
    status: TokenReviewStatus | None = Field(
        default=None,
        alias="status",
        description="Status is filled in by the server and indicates whether the request can be authenticated.",
    )
