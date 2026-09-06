from pydantic import Field

from kubex_core.models.base import BaseK8sModel


class SecretKeySelector(BaseK8sModel):
    """SecretKeySelector selects a key of a Secret."""

    key: str = Field(
        ...,
        alias="key",
        description="The key of the secret to select from. Must be a valid secret key.",
    )
    name: str | None = Field(
        default=None,
        alias="name",
        description="Name of the referent. This field is effectively required, but due to backwards compatibility is allowed to be empty. Instances of this type with an empty value here are almost certainly wrong. More info: https://kubernetes.io/docs/concepts/overview/working-with-objects/names/#names",
    )
    optional: bool | None = Field(
        default=None,
        alias="optional",
        description="Specify whether the Secret or its key must be defined",
    )
