from pydantic import Field

from kubex.k8s.v1_34.core.v1.container_restart_rule_on_exit_codes import (
    ContainerRestartRuleOnExitCodes,
)
from kubex_core.models.base import BaseK8sModel


class ContainerRestartRule(BaseK8sModel):
    """ContainerRestartRule describes how a container exit is handled."""

    action: str = Field(
        ...,
        alias="action",
        description='Specifies the action taken on a container exit if the requirements are satisfied. The only possible value is "Restart" to restart the container.',
    )
    exit_codes: ContainerRestartRuleOnExitCodes | None = Field(
        default=None,
        alias="exitCodes",
        description="Represents the exit codes to check on container exits.",
    )
