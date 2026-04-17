from kubex.k8s.v1_34.apiextensions_k8s_io.v1.custom_resource_definition_condition import (
    CustomResourceDefinitionCondition,
)
from kubex.k8s.v1_34.apiextensions_k8s_io.v1.custom_resource_definition_names import (
    CustomResourceDefinitionNames,
)
from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class CustomResourceDefinitionStatus(BaseK8sModel):
    """CustomResourceDefinitionStatus indicates the state of the CustomResourceDefinition"""

    accepted_names: CustomResourceDefinitionNames | None = Field(
        default=None,
        alias="acceptedNames",
        description="acceptedNames are the names that are actually being used to serve discovery. They may be different than the names in spec.",
    )
    conditions: list[CustomResourceDefinitionCondition] | None = Field(
        default=None,
        alias="conditions",
        description="conditions indicate state for particular aspects of a CustomResourceDefinition",
    )
    stored_versions: list[str] | None = Field(
        default=None,
        alias="storedVersions",
        description="storedVersions lists all versions of CustomResources that were ever persisted. Tracking these versions allows a migration path for stored versions in etcd. The field is mutable so a migration controller can finish a migration to another version (ensuring no old objects are left in storage), and then remove the rest of the versions from this list. Versions may not be removed from `spec.versions` while they exist in this list.",
    )
