from kubex.k8s.v1_32.storagemigration.v1alpha1.group_version_resource import (
    GroupVersionResource,
)
from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class StorageVersionMigrationSpec(BaseK8sModel):
    """Spec of the storage version migration."""

    continue_token: str | None = Field(
        default=None,
        alias="continueToken",
        description='The token used in the list options to get the next chunk of objects to migrate. When the .status.conditions indicates the migration is "Running", users can use this token to check the progress of the migration.',
    )
    resource: GroupVersionResource = Field(
        ...,
        alias="resource",
        description="The resource that is being migrated. The migrator sends requests to the endpoint serving the resource. Immutable.",
    )
