from pydantic import Field

from kubex_core.models.base import BaseK8sModel


class Subject(BaseK8sModel):
    """Subject contains a reference to the object or user identities a role binding applies to. This can either hold a direct API object reference, or a value for non-objects such as user and group names."""

    api_group: str | None = Field(
        default=None,
        alias="apiGroup",
        description='APIGroup holds the API group of the referenced subject. Defaults to "" for ServiceAccount subjects. Defaults to "rbac.authorization.k8s.io" for User and Group subjects.',
    )
    kind: str = Field(
        ...,
        alias="kind",
        description='Kind of object being referenced. Values defined by this API group are "User", "Group", and "ServiceAccount". If the Authorizer does not recognized the kind value, the Authorizer should report an error.',
    )
    name: str = Field(
        ..., alias="name", description="Name of the object being referenced."
    )
    namespace: str | None = Field(
        default=None,
        alias="namespace",
        description='Namespace of the referenced object. If the object kind is non-namespace, such as "User" or "Group", and this value is not empty the Authorizer should report an error.',
    )
