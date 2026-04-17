from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class SelfSubjectRulesReviewSpec(BaseK8sModel):
    """SelfSubjectRulesReviewSpec defines the specification for SelfSubjectRulesReview."""

    namespace: str | None = Field(
        default=None,
        alias="namespace",
        description="Namespace to evaluate rules for. Required.",
    )
