from kubex.k8s.v1_36.core.v1.node_runtime_handler_features import (
    NodeRuntimeHandlerFeatures,
)
from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class NodeRuntimeHandler(BaseK8sModel):
    """NodeRuntimeHandler is a set of runtime handler information."""

    features: NodeRuntimeHandlerFeatures | None = Field(
        default=None, alias="features", description="Supported features."
    )
    name: str | None = Field(
        default=None,
        alias="name",
        description="Runtime handler name. Empty for the default runtime handler.",
    )
