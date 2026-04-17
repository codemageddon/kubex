from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class FlowDistinguisherMethod(BaseK8sModel):
    """FlowDistinguisherMethod specifies the method of a flow distinguisher."""

    type_: str = Field(
        ...,
        alias="type",
        description='`type` is the type of flow distinguisher method The supported types are "ByUser" and "ByNamespace". Required.',
    )
