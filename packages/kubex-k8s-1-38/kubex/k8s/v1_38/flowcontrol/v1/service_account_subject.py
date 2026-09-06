from pydantic import Field

from kubex_core.models.base import BaseK8sModel


class ServiceAccountSubject(BaseK8sModel):
    """ServiceAccountSubject holds detailed information for service-account-kind subject."""

    name: str = Field(
        ...,
        alias="name",
        description='`name` is the name of matching ServiceAccount objects, or "*" to match regardless of name. Required.',
    )
    namespace: str = Field(
        ...,
        alias="namespace",
        description="`namespace` is the namespace of matching ServiceAccount objects. Required.",
    )
