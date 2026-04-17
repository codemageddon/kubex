from __future__ import annotations

from typing import Literal

from kubex.k8s.v1_33.storagemigration.v1alpha1.storage_version_migration import (
    StorageVersionMigration,
)
from kubex_core.models.list_entity import ListEntity
from kubex_core.models.metadata import ListMetadata
from pydantic import Field


class StorageVersionMigrationList(ListEntity[StorageVersionMigration]):
    """StorageVersionMigrationList is a collection of storage version migrations."""

    api_version: Literal["storagemigration.k8s.io/v1alpha1"] = Field(
        default="storagemigration.k8s.io/v1alpha1",
        alias="apiVersion",
        description="APIVersion defines the versioned schema of this representation of an object. Servers should convert recognized schemas to the latest internal value, and may reject unrecognized values. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#resources",
    )
    items: list[StorageVersionMigration] = Field(
        ..., alias="items", description="Items is the list of StorageVersionMigration"
    )
    kind: Literal["StorageVersionMigrationList"] = Field(
        default="StorageVersionMigrationList",
        alias="kind",
        description="Kind is a string value representing the REST resource this object represents. Servers may infer this from the endpoint the client submits requests to. Cannot be updated. In CamelCase. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds",
    )
    metadata: ListMetadata = Field(
        ...,
        alias="metadata",
        description="Standard list metadata More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#metadata",
    )


StorageVersionMigration.__RESOURCE_CONFIG__._list_model = StorageVersionMigrationList
