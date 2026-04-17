from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class ComponentCondition(BaseK8sModel):
    """Information about the condition of a component."""

    error: str | None = Field(
        default=None,
        alias="error",
        description="Condition error code for a component. For example, a health check error code.",
    )
    message: str | None = Field(
        default=None,
        alias="message",
        description="Message about the condition for a component. For example, information about a health check.",
    )
    status: str = Field(
        ...,
        alias="status",
        description='Status of the condition for a component. Valid values for "Healthy": "True", "False", or "Unknown".',
    )
    type_: str = Field(
        ...,
        alias="type",
        description='Type of condition for a component. Valid value: "Healthy"',
    )
