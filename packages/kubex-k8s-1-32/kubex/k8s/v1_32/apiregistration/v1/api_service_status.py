from kubex.k8s.v1_32.apiregistration.v1.api_service_condition import APIServiceCondition
from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class APIServiceStatus(BaseK8sModel):
    """APIServiceStatus contains derived information about an API server"""

    conditions: list[APIServiceCondition] | None = Field(
        default=None,
        alias="conditions",
        description="Current service state of apiService.",
    )
