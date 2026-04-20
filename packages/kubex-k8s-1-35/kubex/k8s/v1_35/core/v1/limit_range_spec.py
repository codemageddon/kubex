from pydantic import Field

from kubex.k8s.v1_35.core.v1.limit_range_item import LimitRangeItem
from kubex_core.models.base import BaseK8sModel


class LimitRangeSpec(BaseK8sModel):
    """LimitRangeSpec defines a min/max usage limit for resources that match on kind."""

    limits: list[LimitRangeItem] = Field(
        ...,
        alias="limits",
        description="Limits is the list of LimitRangeItem objects that are enforced.",
    )
