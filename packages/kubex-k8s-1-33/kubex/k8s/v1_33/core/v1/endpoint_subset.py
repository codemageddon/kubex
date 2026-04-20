from pydantic import Field

from kubex.k8s.v1_33.core.v1.endpoint_address import EndpointAddress
from kubex.k8s.v1_33.core.v1.endpoint_port import EndpointPort
from kubex_core.models.base import BaseK8sModel


class EndpointSubset(BaseK8sModel):
    """EndpointSubset is a group of addresses with a common set of ports. The expanded set of endpoints is the Cartesian product of Addresses x Ports. For example, given: { Addresses: [{"ip": "10.10.1.1"}, {"ip": "10.10.2.2"}], Ports: [{"name": "a", "port": 8675}, {"name": "b", "port": 309}] } The resulting set of endpoints can be viewed as: a: [ 10.10.1.1:8675, 10.10.2.2:8675 ], b: [ 10.10.1.1:309, 10.10.2.2:309 ] Deprecated: This API is deprecated in v1.33+."""

    addresses: list[EndpointAddress] | None = Field(
        default=None,
        alias="addresses",
        description="IP addresses which offer the related ports that are marked as ready. These endpoints should be considered safe for load balancers and clients to utilize.",
    )
    not_ready_addresses: list[EndpointAddress] | None = Field(
        default=None,
        alias="notReadyAddresses",
        description="IP addresses which offer the related ports but are not currently marked as ready because they have not yet finished starting, have recently failed a readiness check, or have recently failed a liveness check.",
    )
    ports: list[EndpointPort] | None = Field(
        default=None,
        alias="ports",
        description="Port numbers available on the related IP addresses.",
    )
