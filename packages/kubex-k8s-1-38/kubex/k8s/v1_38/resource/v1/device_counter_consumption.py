from pydantic import Field

from kubex.k8s.v1_38.resource.v1.counter import Counter
from kubex_core.models.base import BaseK8sModel


class DeviceCounterConsumption(BaseK8sModel):
    """DeviceCounterConsumption defines a set of counters that a device will consume from a CounterSet."""

    compatibility_groups: list[str] | None = Field(
        default=None,
        alias="compatibilityGroups",
        description='CompatibilityGroups is a list of opaque group names for this counter set consumption. Devices that consume counters from the same counter set may only be allocated at the same time ("co-allocated") if they all share at least one common group: the intersection of the CompatibilityGroups of all co-allocated devices on that counter set must be non-empty. Devices that consume from different counter sets are never compared via this field. An unset field, an explicit nil, and an empty list are equivalent and mean "no groups": such a device is only co-allocatable with sibling devices on the same counter set that also have no groups, and is never co-allocatable with a device that declares one or more groups. Group names are opaque and meaningful only within the publishing driver\'s pool. The maximum number of groups is 2, and the names must be unique.',
    )
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
