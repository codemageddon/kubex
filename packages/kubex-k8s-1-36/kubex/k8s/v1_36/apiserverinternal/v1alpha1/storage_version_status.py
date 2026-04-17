from kubex.k8s.v1_36.apiserverinternal.v1alpha1.server_storage_version import (
    ServerStorageVersion,
)
from kubex.k8s.v1_36.apiserverinternal.v1alpha1.storage_version_condition import (
    StorageVersionCondition,
)
from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class StorageVersionStatus(BaseK8sModel):
    """API server instances report the versions they can decode and the version they encode objects to when persisting objects in the backend."""

    common_encoding_version: str | None = Field(
        default=None,
        alias="commonEncodingVersion",
        description="commonEncodingVersion is set to an encoding storage version if all API server instances share that same version. If they don't share one storage version, this field is left empty. API servers should finish updating its storageVersionStatus entry before serving write operations, so that this field will be in sync with the reality.",
    )
    conditions: list[StorageVersionCondition] | None = Field(
        default=None,
        alias="conditions",
        description="conditions lists the latest available observations of the storageVersion's state.",
    )
    storage_versions: list[ServerStorageVersion] | None = Field(
        default=None,
        alias="storageVersions",
        description="storageVersions lists the reported versions per API server instance.",
    )
