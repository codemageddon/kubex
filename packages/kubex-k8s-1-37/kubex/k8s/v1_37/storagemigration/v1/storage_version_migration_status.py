from pydantic import Field

from kubex.k8s.v1_37.meta.v1.condition import Condition
from kubex_core.models.base import BaseK8sModel


class StorageVersionMigrationStatus(BaseK8sModel):
    """Status of the storage version migration."""

    conditions: list[Condition] | None = Field(
        default=None,
        alias="conditions",
        description="The latest available observations of the migration's current state.",
    )
    resource_version: str | None = Field(
        default=None,
        alias="resourceVersion",
        description="ResourceVersion to compare with the GC cache for performing the migration. This is the current resource version of given group, version and resource when kube-controller-manager first observes this StorageVersionMigration resource.",
    )
