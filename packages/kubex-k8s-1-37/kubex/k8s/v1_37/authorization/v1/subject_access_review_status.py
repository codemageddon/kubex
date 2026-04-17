from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class SubjectAccessReviewStatus(BaseK8sModel):
    """SubjectAccessReviewStatus"""

    allowed: bool = Field(
        ...,
        alias="allowed",
        description="allowed is required. True if the action would be allowed, false otherwise.",
    )
    denied: bool | None = Field(
        default=None,
        alias="denied",
        description="denied is optional. True if the action would be denied, otherwise false. If both allowed is false and denied is false, then the authorizer has no opinion on whether to authorize the action. Denied may not be true if Allowed is true.",
    )
    evaluation_error: str | None = Field(
        default=None,
        alias="evaluationError",
        description="evaluationError is an indication that some error occurred during the authorization check. It is entirely possible to get an error and be able to continue determine authorization status in spite of it. For instance, RBAC can be missing a role, but enough roles are still present and bound to reason about the request.",
    )
    reason: str | None = Field(
        default=None,
        alias="reason",
        description="reason is optional. It indicates why a request was allowed or denied.",
    )
