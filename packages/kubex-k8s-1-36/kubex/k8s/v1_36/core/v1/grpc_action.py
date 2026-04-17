from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class GRPCAction(BaseK8sModel):
    """GRPCAction specifies an action involving a GRPC service."""

    port: int = Field(
        ...,
        alias="port",
        description="Port number of the gRPC service. Number must be in the range 1 to 65535.",
    )
    service: str | None = Field(
        default=None,
        alias="service",
        description="Service is the name of the service to place in the gRPC HealthCheckRequest (see https://github.com/grpc/grpc/blob/master/doc/health-checking.md). If this is not specified, the default behavior is defined by gRPC.",
    )
