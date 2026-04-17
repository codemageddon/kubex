from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class SecretReference(BaseK8sModel):
    """SecretReference represents a Secret Reference. It has enough information to retrieve secret in any namespace"""

    name: str | None = Field(
        default=None,
        alias="name",
        description="name is unique within a namespace to reference a secret resource.",
    )
    namespace: str | None = Field(
        default=None,
        alias="namespace",
        description="namespace defines the space within which the secret name must be unique.",
    )
