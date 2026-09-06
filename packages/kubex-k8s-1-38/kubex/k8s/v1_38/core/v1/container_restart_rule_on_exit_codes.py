from pydantic import Field

from kubex_core.models.base import BaseK8sModel


class ContainerRestartRuleOnExitCodes(BaseK8sModel):
    """ContainerRestartRuleOnExitCodes describes the condition for handling an exited container based on its exit codes."""

    operator: str = Field(
        ...,
        alias="operator",
        description="Represents the relationship between the container exit code(s) and the specified values. Possible values are: - In: the requirement is satisfied if the container exit code is in the set of specified values. - NotIn: the requirement is satisfied if the container exit code is not in the set of specified values.",
    )
    values: list[int] | None = Field(
        default=None,
        alias="values",
        description="Specifies the set of values to check for container exit codes. At most 255 elements are allowed.",
    )
