from kubex.k8s.v1_33.batch.v1.pod_failure_policy_on_exit_codes_requirement import (
    PodFailurePolicyOnExitCodesRequirement,
)
from kubex.k8s.v1_33.batch.v1.pod_failure_policy_on_pod_conditions_pattern import (
    PodFailurePolicyOnPodConditionsPattern,
)
from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class PodFailurePolicyRule(BaseK8sModel):
    """PodFailurePolicyRule describes how a pod failure is handled when the requirements are met. One of onExitCodes and onPodConditions, but not both, can be used in each rule."""

    action: str = Field(
        ...,
        alias="action",
        description="Specifies the action taken on a pod failure when the requirements are satisfied. Possible values are: - FailJob: indicates that the pod's job is marked as Failed and all running pods are terminated. - FailIndex: indicates that the pod's index is marked as Failed and will not be restarted. - Ignore: indicates that the counter towards the .backoffLimit is not incremented and a replacement pod is created. - Count: indicates that the pod is handled in the default way - the counter towards the .backoffLimit is incremented. Additional values are considered to be added in the future. Clients should react to an unknown action by skipping the rule.",
    )
    on_exit_codes: PodFailurePolicyOnExitCodesRequirement | None = Field(
        default=None,
        alias="onExitCodes",
        description="Represents the requirement on the container exit codes.",
    )
    on_pod_conditions: list[PodFailurePolicyOnPodConditionsPattern] | None = Field(
        default=None,
        alias="onPodConditions",
        description="Represents the requirement on the pod conditions. The requirement is represented as a list of pod condition patterns. The requirement is satisfied if at least one pattern matches an actual pod condition. At most 20 elements are allowed.",
    )
