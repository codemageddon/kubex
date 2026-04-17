from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class CrossVersionObjectReference(BaseK8sModel):
    """CrossVersionObjectReference contains enough information to let you identify the referred resource."""

    api_version: str | None = Field(
        default=None,
        alias="apiVersion",
        description="apiVersion is the API version of the referent",
    )
    kind: str = Field(
        ...,
        alias="kind",
        description="kind is the kind of the referent; More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds",
    )
    name: str = Field(
        ...,
        alias="name",
        description="name is the name of the referent; More info: https://kubernetes.io/docs/concepts/overview/working-with-objects/names/#names",
    )
