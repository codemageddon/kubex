from kubex.k8s.v1_35.resource.v1beta1.counter import Counter
from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class DeviceCounterConsumption(BaseK8sModel):
    """DeviceCounterConsumption defines a set of counters that a device will consume from a CounterSet."""

    counter_set: str = Field(
        ...,
        alias="counterSet",
        description="CounterSet is the name of the set from which the counters defined will be consumed.",
    )
    counters: dict[str, Counter] = Field(
        ...,
        alias="counters",
        description="Counters defines the counters that will be consumed by the device. The maximum number of counters is 32.",
    )
