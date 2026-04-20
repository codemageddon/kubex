from pydantic import Field

from kubex.k8s.v1_34.flowcontrol.v1.flow_schema_condition import FlowSchemaCondition
from kubex_core.models.base import BaseK8sModel


class FlowSchemaStatus(BaseK8sModel):
    """FlowSchemaStatus represents the current state of a FlowSchema."""

    conditions: list[FlowSchemaCondition] | None = Field(
        default=None,
        alias="conditions",
        description="`conditions` is a list of the current states of FlowSchema.",
    )
