from pydantic import Field

from kubex.k8s.v1_34.networking.v1beta1.parent_reference import ParentReference
from kubex_core.models.base import BaseK8sModel


class IPAddressSpec(BaseK8sModel):
    """IPAddressSpec describe the attributes in an IP Address."""

    parent_ref: ParentReference = Field(
        ...,
        alias="parentRef",
        description="ParentRef references the resource that an IPAddress is attached to. An IPAddress must reference a parent object.",
    )
