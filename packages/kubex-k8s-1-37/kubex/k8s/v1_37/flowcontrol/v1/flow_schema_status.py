from kubex.k8s.v1_37.flowcontrol.v1.flow_schema_condition import FlowSchemaCondition
from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class FlowSchemaStatus(BaseK8sModel):
    """FlowSchemaStatus represents the current state of a FlowSchema."""

    conditions: list[FlowSchemaCondition] | None = Field(
        default=None,
        alias="conditions",
        description="`conditions` is a list of the current states of FlowSchema.",
    )
