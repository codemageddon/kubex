from pydantic import Field

from kubex_core.models.base import BaseK8sModel


class EvictionResponder(BaseK8sModel):
    """EvictionResponder allows you to specify the responder reacting to an Eviction. Responders should observe and communicate through the Eviction Resource API to help with the graceful eviction of a target (e.g. termination of a pod)."""

    name: str = Field(
        ...,
        alias="name",
        description='name allows you to identify the responder responding to the Eviction. It must be a valid domain-prefixed key (such as "acme.io/foo"). Domain names *.k8s.io and *.kubernetes.io are reserved. This field must be unique for each responder. This field is required.',
    )
    priority: int = Field(
        ...,
        alias="priority",
        description="priority for this responder. Higher priorities are selected first by the evictionrequest-controller. If there are responders with the same priority, the responder whose domain name comes first in the alphabetical higher domain order, will be picked. This means that the top domain labels are compared alphabetically first, followed by the lower domain labels. The key is compared last. The responder that is the managing controller of the pod should set the value of this field to 10000 to allow both for preemption or fallback registration by other responders. The minimum value is 0 and the maximum value is 100000. The interval 0-999 is reserved for responders with *.k8s.io suffix. This field is required.",
    )
