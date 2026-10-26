from pydantic import Field

from kubex.k8s.v1_38.resource.v1beta2.counter import Counter
from kubex_core.models.base import BaseK8sModel
from kubex_core.models.types import NullAsEmptyDict


class CounterSet(BaseK8sModel):
    """CounterSet defines a named set of counters that are available to be used by devices defined in the ResourcePool. The counters are not allocatable by themselves, but can be referenced by devices. When a device is allocated, the portion of counters it uses will no longer be available for use by other devices."""

    counters: NullAsEmptyDict[Counter] = Field(
        ...,
        alias="counters",
        description="counters defines the set of counters for this CounterSet The name of each counter must be unique in that set and must be a DNS label. The maximum number of counters is 32.",
    )
    name: str = Field(
        ...,
        alias="name",
        description="name defines the name of the counter set. It must be a DNS label.",
    )
