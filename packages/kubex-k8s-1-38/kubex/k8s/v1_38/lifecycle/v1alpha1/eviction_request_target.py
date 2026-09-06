from pydantic import Field

from kubex.k8s.v1_38.lifecycle.v1alpha1.eviction_request_pod_reference import (
    EvictionRequestPodReference,
)
from kubex_core.models.base import BaseK8sModel


class EvictionRequestTarget(BaseK8sModel):
    """EvictionRequestTarget contains a reference to an object that should be evicted."""

    pod: EvictionRequestPodReference | None = Field(
        default=None,
        alias="pod",
        description="pod references a pod that is subject to eviction/termination. Pods that are part of a PodGroup (.spec.schedulingGroup is set) are not supported.",
    )
