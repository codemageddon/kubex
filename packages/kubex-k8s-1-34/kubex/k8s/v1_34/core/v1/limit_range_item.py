from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class LimitRangeItem(BaseK8sModel):
    """LimitRangeItem defines a min/max usage limit for any resource that matches on kind."""

    default: dict[str, str] | None = Field(
        default=None,
        alias="default",
        description="Default resource requirement limit value by resource name if resource limit is omitted.",
    )
    default_request: dict[str, str] | None = Field(
        default=None,
        alias="defaultRequest",
        description="DefaultRequest is the default resource requirement request value by resource name if resource request is omitted.",
    )
    max: dict[str, str] | None = Field(
        default=None,
        alias="max",
        description="Max usage constraints on this kind by resource name.",
    )
    max_limit_request_ratio: dict[str, str] | None = Field(
        default=None,
        alias="maxLimitRequestRatio",
        description="MaxLimitRequestRatio if specified, the named resource must have a request and limit that are both non-zero where limit divided by request is less than or equal to the enumerated value; this represents the max burst for the named resource.",
    )
    min: dict[str, str] | None = Field(
        default=None,
        alias="min",
        description="Min usage constraints on this kind by resource name.",
    )
    type_: str = Field(
        ..., alias="type", description="Type of resource that this limit applies to."
    )
