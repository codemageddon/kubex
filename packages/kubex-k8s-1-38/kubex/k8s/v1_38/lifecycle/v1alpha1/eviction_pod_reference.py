from pydantic import Field

from kubex_core.models.base import BaseK8sModel


class EvictionPodReference(BaseK8sModel):
    """EvictionPodReference contains enough information to locate the referenced pod inside the same namespace."""

    name: str = Field(
        ..., alias="name", description="name of the target. This field is required."
    )
    uid: str = Field(
        ...,
        alias="uid",
        description="uid of the target. It can be found in .metadata.uid of the target and is a lowercase UUID in 8-4-4-4-12 format. This field is required.",
    )
