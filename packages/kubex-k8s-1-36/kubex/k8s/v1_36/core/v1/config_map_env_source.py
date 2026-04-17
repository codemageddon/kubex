from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class ConfigMapEnvSource(BaseK8sModel):
    """ConfigMapEnvSource selects a ConfigMap to populate the environment variables with. The contents of the target ConfigMap's Data field will represent the key-value pairs as environment variables."""

    name: str | None = Field(
        default=None,
        alias="name",
        description="Name of the referent. This field is effectively required, but due to backwards compatibility is allowed to be empty. Instances of this type with an empty value here are almost certainly wrong. More info: https://kubernetes.io/docs/concepts/overview/working-with-objects/names/#names",
    )
    optional: bool | None = Field(
        default=None,
        alias="optional",
        description="Specify whether the ConfigMap must be defined",
    )
