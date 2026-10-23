from pydantic import Field

from kubex_core.models.base import BaseK8sModel


class GRPCAction(BaseK8sModel):
    """GRPCAction specifies an action involving a GRPC service."""

    mode: str | None = Field(
        default=None,
        alias="mode",
        description='mode specifies the connection mode for the gRPC health probe. Set to "TLS" to use TLS without certificate verification. Set to "Plaintext" to use a plaintext (insecure) connection explicitly. If not specified, the probe uses a plaintext (insecure) connection.',
    )
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
