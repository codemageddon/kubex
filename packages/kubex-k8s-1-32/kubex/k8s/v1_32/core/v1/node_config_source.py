from kubex.k8s.v1_32.core.v1.config_map_node_config_source import (
    ConfigMapNodeConfigSource,
)
from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class NodeConfigSource(BaseK8sModel):
    """NodeConfigSource specifies a source of node configuration. Exactly one subfield (excluding metadata) must be non-nil. This API is deprecated since 1.22"""

    config_map: ConfigMapNodeConfigSource | None = Field(
        default=None,
        alias="configMap",
        description="ConfigMap is a reference to a Node's ConfigMap",
    )
