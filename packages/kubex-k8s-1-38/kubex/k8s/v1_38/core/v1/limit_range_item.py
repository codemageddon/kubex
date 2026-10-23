from pydantic import Field

from kubex_core.models.base import BaseK8sModel


class LimitRangeItem(BaseK8sModel):
    """LimitRangeItem defines a min/max usage limit for any resource that matches on kind."""

    default: dict[str, str] | None = Field(
        default=None,
        alias="default",
        description="default specifies resource limit values by resource name. These are applied to containers which do not specify their own limits for those resources.",
    )
    default_request: dict[str, str] | None = Field(
        default=None,
        alias="defaultRequest",
        description="defaultRequest specifies resource request values by resource name. These are applied to containers which do not specify their own requests for those resources.",
    )
    max: dict[str, str] | None = Field(
        default=None,
        alias="max",
        description="max usage constraints on this kind by resource name.",
    )
    max_limit_request_ratio: dict[str, str] | None = Field(
        default=None,
        alias="maxLimitRequestRatio",
        description="maxLimitRequestRatio if specified, the named resource must have a request and limit that are both non-zero where limit divided by request is less than or equal to the enumerated value; this represents the max burst for the named resource.",
    )
    min: dict[str, str] | None = Field(
        default=None,
        alias="min",
        description="min usage constraints on this kind by resource name.",
    )
    type_: str = Field(
        ..., alias="type", description="type of resource that this limit applies to."
    )
