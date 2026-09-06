from pydantic import Field

from kubex_core.models.base import BaseK8sModel


class UncountedTerminatedPods(BaseK8sModel):
    """UncountedTerminatedPods holds UIDs of Pods that have terminated but haven't been accounted in Job status counters."""

    failed: list[str] | None = Field(
        default=None, alias="failed", description="failed holds UIDs of failed Pods."
    )
    succeeded: list[str] | None = Field(
        default=None,
        alias="succeeded",
        description="succeeded holds UIDs of succeeded Pods.",
    )
