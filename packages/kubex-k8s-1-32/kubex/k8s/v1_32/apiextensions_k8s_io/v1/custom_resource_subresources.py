from kubex.k8s.v1_32.apiextensions_k8s_io.v1.custom_resource_subresource_scale import (
    CustomResourceSubresourceScale,
)
from kubex.k8s.v1_32.apiextensions_k8s_io.v1.custom_resource_subresource_status import (
    CustomResourceSubresourceStatus,
)
from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class CustomResourceSubresources(BaseK8sModel):
    """CustomResourceSubresources defines the status and scale subresources for CustomResources."""

    scale: CustomResourceSubresourceScale | None = Field(
        default=None,
        alias="scale",
        description="scale indicates the custom resource should serve a `/scale` subresource that returns an `autoscaling/v1` Scale object.",
    )
    status: CustomResourceSubresourceStatus | None = Field(
        default=None,
        alias="status",
        description="status indicates the custom resource should serve a `/status` subresource. When enabled: 1. requests to the custom resource primary endpoint ignore changes to the `status` stanza of the object. 2. requests to the custom resource `/status` subresource ignore changes to anything other than the `status` stanza of the object.",
    )
