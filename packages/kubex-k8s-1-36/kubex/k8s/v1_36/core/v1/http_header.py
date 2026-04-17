from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class HTTPHeader(BaseK8sModel):
    """HTTPHeader describes a custom header to be used in HTTP probes"""

    name: str = Field(
        ...,
        alias="name",
        description="The header field name. This will be canonicalized upon output, so case-variant names will be understood as the same header.",
    )
    value: str = Field(..., alias="value", description="The header field value")
