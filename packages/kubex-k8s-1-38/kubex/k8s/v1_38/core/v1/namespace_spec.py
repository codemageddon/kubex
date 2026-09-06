from pydantic import Field

from kubex_core.models.base import BaseK8sModel


class NamespaceSpec(BaseK8sModel):
    """NamespaceSpec describes the attributes on a Namespace."""

    finalizers: list[str] | None = Field(
        default=None,
        alias="finalizers",
        description="Finalizers is an opaque list of values that must be empty to permanently remove object from storage. More info: https://kubernetes.io/docs/tasks/administer-cluster/namespaces/",
    )
