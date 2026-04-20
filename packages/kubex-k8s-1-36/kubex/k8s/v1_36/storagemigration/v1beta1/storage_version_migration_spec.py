from pydantic import Field

from kubex.k8s.v1_36.meta.v1.group_resource import GroupResource
from kubex_core.models.base import BaseK8sModel


class StorageVersionMigrationSpec(BaseK8sModel):
    """Spec of the storage version migration."""

    resource: GroupResource = Field(
        ...,
        alias="resource",
        description="The resource that is being migrated. The migrator sends requests to the endpoint serving the resource. Immutable.",
    )
