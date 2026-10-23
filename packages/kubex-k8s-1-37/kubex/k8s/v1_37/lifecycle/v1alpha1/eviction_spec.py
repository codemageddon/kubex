from pydantic import Field

from kubex.k8s.v1_37.lifecycle.v1alpha1.eviction_target import EvictionTarget
from kubex_core.models.base import BaseK8sModel


class EvictionSpec(BaseK8sModel):
    """EvictionSpec is a specification of an Eviction."""

    target: EvictionTarget = Field(
        ...,
        alias="target",
        description="target contains a reference to an object (e.g. a pod) that should be evicted. This field is required and immutable.",
    )
