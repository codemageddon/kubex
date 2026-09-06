from pydantic import Field

from kubex.k8s.v1_37.meta.v1.condition import Condition
from kubex_core.models.base import BaseK8sModel


class EvictionRequestStatus(BaseK8sModel):
    """EvictionRequestStatus represents the last observed status of the eviction request."""

    conditions: list[Condition] | None = Field(
        default=None,
        alias="conditions",
        description="conditions contain information about the eviction request. EvictionRequest specific conditions are: TargetEvicted or Failed (managed by evictionrequest-controller). - Failed means that the eviction request is no longer being processed by any eviction responder. This can happen if the request is canceled or if no responder managed to evict the target (e.g. terminate or delete a pod). - TargetEvicted means that the target has been evicted (e.g. a pod has been terminated or deleted). These conditions can be reset if the eviction was unsuccessful and a new Eviction intent has been submitted. The maximum length of the conditions list is 100.",
    )
    observed_generation: int | None = Field(
        default=None,
        alias="observedGeneration",
        description="observedGeneration is EvictionRequest's .metadata.generation observed by the evictionrequest-controller. The observed generation value cannot be negative and can only be incremented. The minimum value is 1. This field is managed by evictionrequest-controller.",
    )
