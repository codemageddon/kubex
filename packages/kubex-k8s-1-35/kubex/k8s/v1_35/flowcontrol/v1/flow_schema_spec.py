from pydantic import Field

from kubex.k8s.v1_35.flowcontrol.v1.flow_distinguisher_method import (
    FlowDistinguisherMethod,
)
from kubex.k8s.v1_35.flowcontrol.v1.policy_rules_with_subjects import (
    PolicyRulesWithSubjects,
)
from kubex.k8s.v1_35.flowcontrol.v1.priority_level_configuration_reference import (
    PriorityLevelConfigurationReference,
)
from kubex_core.models.base import BaseK8sModel


class FlowSchemaSpec(BaseK8sModel):
    """FlowSchemaSpec describes how the FlowSchema's specification looks like."""

    distinguisher_method: FlowDistinguisherMethod | None = Field(
        default=None,
        alias="distinguisherMethod",
        description="`distinguisherMethod` defines how to compute the flow distinguisher for requests that match this schema. `nil` specifies that the distinguisher is disabled and thus will always be the empty string.",
    )
    matching_precedence: int | None = Field(
        default=None,
        alias="matchingPrecedence",
        description="`matchingPrecedence` is used to choose among the FlowSchemas that match a given request. The chosen FlowSchema is among those with the numerically lowest (which we take to be logically highest) MatchingPrecedence. Each MatchingPrecedence value must be ranged in [1,10000]. Note that if the precedence is not specified, it will be set to 1000 as default.",
    )
    priority_level_configuration: PriorityLevelConfigurationReference = Field(
        ...,
        alias="priorityLevelConfiguration",
        description="`priorityLevelConfiguration` should reference a PriorityLevelConfiguration in the cluster. If the reference cannot be resolved, the FlowSchema will be ignored and marked as invalid in its status. Required.",
    )
    rules: list[PolicyRulesWithSubjects] | None = Field(
        default=None,
        alias="rules",
        description="`rules` describes which requests will match this flow schema. This FlowSchema matches a request if and only if at least one member of rules matches the request. if it is an empty slice, there will be no requests matching the FlowSchema.",
    )
