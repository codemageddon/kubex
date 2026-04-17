from kubex.k8s.v1_32.core.v1.namespace_condition import NamespaceCondition
from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class NamespaceStatus(BaseK8sModel):
    """NamespaceStatus is information about the current status of a Namespace."""

    conditions: list[NamespaceCondition] | None = Field(
        default=None,
        alias="conditions",
        description="Represents the latest available observations of a namespace's current state.",
    )
    phase: str | None = Field(
        default=None,
        alias="phase",
        description="Phase is the current lifecycle phase of the namespace. More info: https://kubernetes.io/docs/tasks/administer-cluster/namespaces/",
    )
