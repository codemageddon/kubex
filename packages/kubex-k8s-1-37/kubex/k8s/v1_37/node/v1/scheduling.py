from pydantic import Field

from kubex.k8s.v1_37.core.v1.toleration import Toleration
from kubex_core.models.base import BaseK8sModel


class Scheduling(BaseK8sModel):
    """Scheduling specifies the scheduling constraints for nodes supporting a RuntimeClass."""

    node_selector: dict[str, str] | None = Field(
        default=None,
        alias="nodeSelector",
        description="nodeSelector lists labels that must be present on nodes that support this RuntimeClass. Pods using this RuntimeClass can only be scheduled to a node matched by this selector. The RuntimeClass nodeSelector is merged with a pod's existing nodeSelector. Any conflicts will cause the pod to be rejected in admission.",
    )
    tolerations: list[Toleration] | None = Field(
        default=None,
        alias="tolerations",
        description="tolerations are appended (excluding duplicates) to pods running with this RuntimeClass during admission, effectively unioning the set of nodes tolerated by the pod and the RuntimeClass.",
    )
