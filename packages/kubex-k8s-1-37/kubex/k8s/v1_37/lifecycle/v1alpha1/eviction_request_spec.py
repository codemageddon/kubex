from pydantic import Field

from kubex.k8s.v1_37.lifecycle.v1alpha1.eviction_request_target import (
    EvictionRequestTarget,
)
from kubex_core.models.base import BaseK8sModel


class EvictionRequestSpec(BaseK8sModel):
    """EvictionRequestSpec is a specification of an EvictionRequest."""

    intent: str = Field(
        ...,
        alias="intent",
        description="intent specifies the action that should be taken for the specified target. - Eviction means that the requester is interested in the eviction of the target. - Withdrawn means that the requester is no longer interested in the eviction of the target. If all requesters' intents are withdrawn for a common target, the eviction will be canceled. Cancellation consequences: - Inactive responders will never run. - Active responders are expected to cancel the eviction. - Completed or Interrupted responders should not take any action.",
    )
    requester: str = Field(
        ...,
        alias="requester",
        description='requester allows you to identify the entity, that requested the eviction of the target. It must be a valid domain-prefixed key (such as "acme.io/foo"). Domain names *.k8s.io and *.kubernetes.io are reserved. This field is required and immutable.',
    )
    target: EvictionRequestTarget = Field(
        ...,
        alias="target",
        description="target contains a reference to an object (e.g. a pod) that should be evicted. This field is required and immutable.",
    )
