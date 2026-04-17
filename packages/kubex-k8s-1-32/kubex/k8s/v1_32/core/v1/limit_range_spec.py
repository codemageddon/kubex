from kubex.k8s.v1_32.core.v1.limit_range_item import LimitRangeItem
from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class LimitRangeSpec(BaseK8sModel):
    """LimitRangeSpec defines a min/max usage limit for resources that match on kind."""

    limits: list[LimitRangeItem] = Field(
        ...,
        alias="limits",
        description="Limits is the list of LimitRangeItem objects that are enforced.",
    )
