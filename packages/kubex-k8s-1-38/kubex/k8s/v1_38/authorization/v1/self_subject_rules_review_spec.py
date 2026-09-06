from pydantic import Field

from kubex_core.models.base import BaseK8sModel


class SelfSubjectRulesReviewSpec(BaseK8sModel):
    """SelfSubjectRulesReviewSpec defines the specification for SelfSubjectRulesReview."""

    namespace: str | None = Field(
        default=None,
        alias="namespace",
        description="namespace to evaluate rules for. Required.",
    )
