from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class ResourceQuotaStatus(BaseK8sModel):
    """ResourceQuotaStatus defines the enforced hard limits and observed use."""

    hard: dict[str, str] | None = Field(
        default=None,
        alias="hard",
        description="Hard is the set of enforced hard limits for each named resource. More info: https://kubernetes.io/docs/concepts/policy/resource-quotas/",
    )
    used: dict[str, str] | None = Field(
        default=None,
        alias="used",
        description="Used is the current observed total usage of the resource in the namespace.",
    )
