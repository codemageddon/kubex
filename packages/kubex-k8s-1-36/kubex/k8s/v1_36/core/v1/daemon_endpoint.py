from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class DaemonEndpoint(BaseK8sModel):
    """DaemonEndpoint contains information about a single Daemon endpoint."""

    port: int = Field(
        ..., alias="Port", description="Port number of the given endpoint."
    )
