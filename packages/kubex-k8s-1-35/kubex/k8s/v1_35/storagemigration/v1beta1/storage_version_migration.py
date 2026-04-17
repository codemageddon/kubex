from __future__ import annotations

from typing import ClassVar, Literal

from kubex.k8s.v1_35.storagemigration.v1beta1.storage_version_migration_spec import (
    StorageVersionMigrationSpec,
)
from kubex.k8s.v1_35.storagemigration.v1beta1.storage_version_migration_status import (
    StorageVersionMigrationStatus,
)
from kubex_core.models.interfaces import ClusterScopedEntity, HasStatusSubresource
from kubex_core.models.resource_config import ResourceConfig, Scope
from pydantic import Field


class StorageVersionMigration(ClusterScopedEntity, HasStatusSubresource):
    """StorageVersionMigration represents a migration of stored data to the latest storage version."""

    __RESOURCE_CONFIG__: ClassVar[ResourceConfig["StorageVersionMigration"]] = (
        ResourceConfig["StorageVersionMigration"](
            version="v1beta1",
            kind="StorageVersionMigration",
            group="storagemigration.k8s.io",
            plural="storageversionmigrations",
            scope=Scope.CLUSTER,
        )
    )
    api_version: Literal["storagemigration.k8s.io/v1beta1"] = Field(
        default="storagemigration.k8s.io/v1beta1",
        alias="apiVersion",
        description="APIVersion defines the versioned schema of this representation of an object. Servers should convert recognized schemas to the latest internal value, and may reject unrecognized values. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#resources",
    )
    kind: Literal["StorageVersionMigration"] = Field(
        default="StorageVersionMigration",
        alias="kind",
        description="Kind is a string value representing the REST resource this object represents. Servers may infer this from the endpoint the client submits requests to. Cannot be updated. In CamelCase. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds",
    )
    spec: StorageVersionMigrationSpec | None = Field(
        default=None, alias="spec", description="Specification of the migration."
    )
    status: StorageVersionMigrationStatus | None = Field(
        default=None, alias="status", description="Status of the migration."
    )
