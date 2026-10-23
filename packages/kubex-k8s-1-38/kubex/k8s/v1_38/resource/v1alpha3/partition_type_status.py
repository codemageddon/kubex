from pydantic import Field

from kubex_core.models.base import BaseK8sModel


class PartitionTypeStatus(BaseK8sModel):
    """PartitionTypeStatus reports allocatability for a single partition type, identified by the value of a grouping attribute."""

    allocatable: int = Field(
        ...,
        alias="allocatable",
        description="allocatable is the number of additional devices of this partition type that could still be allocated given current shared-counter consumption.",
    )
    attribute: str = Field(
        ...,
        alias="attribute",
        description="attribute is the fully qualified name of the device attribute whose value groups this entry. It is the PartitionTypeAttribute declared by the devices' own slice, or the default named in the request when their slice declares none.",
    )
    total: int = Field(
        ...,
        alias="total",
        description="total is the number of devices of this partition type in the pool.",
    )
    type_: str = Field(
        ...,
        alias="type",
        description='type is the partition type value (e.g. "Full" or "Half").',
    )
