from pydantic import Field

from kubex_core.models.base import BaseK8sModel


class ComponentCondition(BaseK8sModel):
    """Information about the condition of a component."""

    error: str | None = Field(
        default=None,
        alias="error",
        description="error is the condition error code for a component. For example, a health check error code.",
    )
    message: str | None = Field(
        default=None,
        alias="message",
        description="message about the condition for a component. For example, information about a health check.",
    )
    status: str = Field(
        ...,
        alias="status",
        description='status of the condition for a component. Valid values for "Healthy": "True", "False", or "Unknown".',
    )
    type_: str = Field(
        ...,
        alias="type",
        description='type of condition for a component. Valid value: "Healthy"',
    )
