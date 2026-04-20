from pydantic import Field

from kubex_core.models.base import BaseK8sModel


class LocalObjectReference(BaseK8sModel):
    """LocalObjectReference contains enough information to let you locate the referenced object inside the same namespace."""

    name: str | None = Field(
        default=None,
        alias="name",
        description="Name of the referent. This field is effectively required, but due to backwards compatibility is allowed to be empty. Instances of this type with an empty value here are almost certainly wrong. More info: https://kubernetes.io/docs/concepts/overview/working-with-objects/names/#names",
    )
