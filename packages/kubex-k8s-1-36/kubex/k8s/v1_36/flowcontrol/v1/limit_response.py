from kubex.k8s.v1_36.flowcontrol.v1.queuing_configuration import QueuingConfiguration
from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class LimitResponse(BaseK8sModel):
    """LimitResponse defines how to handle requests that can not be executed right now."""

    queuing: QueuingConfiguration | None = Field(
        default=None,
        alias="queuing",
        description='`queuing` holds the configuration parameters for queuing. This field may be non-empty only if `type` is `"Queue"`.',
    )
    type_: str = Field(
        ...,
        alias="type",
        description='`type` is "Queue" or "Reject". "Queue" means that requests that can not be executed upon arrival are held in a queue until they can be executed or a queuing limit is reached. "Reject" means that requests that can not be executed upon arrival are rejected. Required.',
    )
