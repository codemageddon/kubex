from pydantic import Field

from kubex_core.models.base import BaseK8sModel


class ContainerExtendedResourceRequest(BaseK8sModel):
    """ContainerExtendedResourceRequest has the mapping of container name, extended resource name to the device request name."""

    container_name: str = Field(
        ...,
        alias="containerName",
        description="The name of the container requesting resources.",
    )
    request_name: str = Field(
        ...,
        alias="requestName",
        description="The name of the request in the special ResourceClaim which corresponds to the extended resource.",
    )
    resource_name: str = Field(
        ...,
        alias="resourceName",
        description="The name of the extended resource in that container which gets backed by DRA.",
    )
