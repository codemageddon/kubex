from kubex.k8s.v1_33.resource.v1alpha3.counter import Counter
from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class DeviceCounterConsumption(BaseK8sModel):
    """DeviceCounterConsumption defines a set of counters that a device will consume from a CounterSet."""

    counter_set: str = Field(
        ...,
        alias="counterSet",
        description="CounterSet defines the set from which the counters defined will be consumed.",
    )
    counters: dict[str, Counter] = Field(
        ...,
        alias="counters",
        description="Counters defines the Counter that will be consumed by the device. The maximum number counters in a device is 32. In addition, the maximum number of all counters in all devices is 1024 (for example, 64 devices with 16 counters each).",
    )
