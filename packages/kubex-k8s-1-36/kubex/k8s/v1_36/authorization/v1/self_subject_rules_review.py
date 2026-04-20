from __future__ import annotations

from typing import ClassVar, Literal

from pydantic import Field

from kubex.k8s.v1_36.authorization.v1.self_subject_rules_review_spec import (
    SelfSubjectRulesReviewSpec,
)
from kubex.k8s.v1_36.authorization.v1.subject_rules_review_status import (
    SubjectRulesReviewStatus,
)
from kubex_core.models.interfaces import ClusterScopedEntity
from kubex_core.models.resource_config import ResourceConfig, Scope


class SelfSubjectRulesReview(ClusterScopedEntity):
    """SelfSubjectRulesReview enumerates the set of actions the current user can perform within a namespace. The returned list of actions may be incomplete depending on the server's authorization mode, and any errors experienced during the evaluation. SelfSubjectRulesReview should be used by UIs to show/hide actions, or to quickly let an end user reason about their permissions. It should NOT Be used by external systems to drive authorization decisions as this raises confused deputy, cache lifetime/revocation, and correctness concerns. SubjectAccessReview, and LocalAccessReview are the correct way to defer authorization decisions to the API server."""

    __RESOURCE_CONFIG__: ClassVar[ResourceConfig["SelfSubjectRulesReview"]] = (
        ResourceConfig["SelfSubjectRulesReview"](
            version="v1",
            kind="SelfSubjectRulesReview",
            group="authorization.k8s.io",
            plural="selfsubjectrulesreviews",
            scope=Scope.CLUSTER,
        )
    )
    api_version: Literal["authorization.k8s.io/v1"] = Field(
        default="authorization.k8s.io/v1",
        alias="apiVersion",
        description="APIVersion defines the versioned schema of this representation of an object. Servers should convert recognized schemas to the latest internal value, and may reject unrecognized values. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#resources",
    )
    kind: Literal["SelfSubjectRulesReview"] = Field(
        default="SelfSubjectRulesReview",
        alias="kind",
        description="Kind is a string value representing the REST resource this object represents. Servers may infer this from the endpoint the client submits requests to. Cannot be updated. In CamelCase. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds",
    )
    spec: SelfSubjectRulesReviewSpec = Field(
        ...,
        alias="spec",
        description="spec holds information about the request being evaluated.",
    )
    status: SubjectRulesReviewStatus | None = Field(
        default=None,
        alias="status",
        description="status is filled in by the server and indicates the set of actions a user can perform.",
    )
