from pydantic import Field

from kubex_core.models.base import BaseK8sModel


class TypedObjectReference(BaseK8sModel):
    """TypedObjectReference contains enough information to let you locate the typed referenced object"""

    api_group: str | None = Field(
        default=None,
        alias="apiGroup",
        description="APIGroup is the group for the resource being referenced. If APIGroup is not specified, the specified Kind must be in the core API group. For any other third-party types, APIGroup is required.",
    )
    kind: str = Field(
        ..., alias="kind", description="Kind is the type of resource being referenced"
    )
    name: str = Field(
        ..., alias="name", description="Name is the name of resource being referenced"
    )
    namespace: str | None = Field(
        default=None,
        alias="namespace",
        description="Namespace is the namespace of resource being referenced Note that when a namespace is specified, a gateway.networking.k8s.io/ReferenceGrant object is required in the referent namespace to allow that namespace's owner to accept the reference. See the ReferenceGrant documentation for details. (Alpha) This field requires the CrossNamespaceVolumeDataSource feature gate to be enabled.",
    )
