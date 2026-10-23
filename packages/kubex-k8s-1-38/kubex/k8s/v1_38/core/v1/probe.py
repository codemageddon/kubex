from pydantic import Field

from kubex.k8s.v1_38.core.v1.exec_action import ExecAction
from kubex.k8s.v1_38.core.v1.grpc_action import GRPCAction
from kubex.k8s.v1_38.core.v1.http_get_action import HTTPGetAction
from kubex.k8s.v1_38.core.v1.tcp_socket_action import TCPSocketAction
from kubex_core.models.base import BaseK8sModel


class Probe(BaseK8sModel):
    """Probe describes a health check to be performed against a container to determine whether it is alive or ready to receive traffic."""

    exec: ExecAction | None = Field(
        default=None,
        alias="exec",
        description="exec specifies a command to execute in the container.",
    )
    failure_threshold: int | None = Field(
        default=None,
        alias="failureThreshold",
        description="failureThreshold is the minimum consecutive failures for the probe to be considered failed after having succeeded. Defaults to 3. Minimum value is 1.",
    )
    grpc: GRPCAction | None = Field(
        default=None,
        alias="grpc",
        description="grpc specifies a GRPC HealthCheckRequest.",
    )
    http_get: HTTPGetAction | None = Field(
        default=None,
        alias="httpGet",
        description="httpGet specifies an HTTP GET request to perform.",
    )
    initial_delay_seconds: int | None = Field(
        default=None,
        alias="initialDelaySeconds",
        description="initialDelaySeconds is the number of seconds after the container has started before liveness probes are initiated. More info: https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle#container-probes",
    )
    period_seconds: int | None = Field(
        default=None,
        alias="periodSeconds",
        description="periodSeconds is how often (in seconds) to perform the probe. Default to 10 seconds. Minimum value is 1.",
    )
    success_threshold: int | None = Field(
        default=None,
        alias="successThreshold",
        description="successThreshold is the minimum consecutive successes for the probe to be considered successful after having failed. Defaults to 1. Must be 1 for liveness and startup. Minimum value is 1.",
    )
    tcp_socket: TCPSocketAction | None = Field(
        default=None,
        alias="tcpSocket",
        description="tcpSocket specifies a connection to a TCP port.",
    )
    termination_grace_period_seconds: int | None = Field(
        default=None,
        alias="terminationGracePeriodSeconds",
        description="terminationGracePeriodSeconds is the optional duration in seconds the pod needs to terminate gracefully upon probe failure. The grace period is the duration in seconds after the processes running in the pod are sent a termination signal and the time when the processes are forcibly halted with a kill signal. Set this value longer than the expected cleanup time for your process. If this value is nil, the pod's terminationGracePeriodSeconds will be used. Otherwise, this value overrides the value provided by the pod spec. Value must be non-negative integer. The value zero indicates stop immediately via the kill signal (no opportunity to shut down). This is a beta field and requires enabling ProbeTerminationGracePeriod feature gate. Minimum value is 1. spec.terminationGracePeriodSeconds is used if unset.",
    )
    timeout_seconds: int | None = Field(
        default=None,
        alias="timeoutSeconds",
        description="timeoutSeconds is the number of seconds after which the probe times out. Defaults to 1 second. Minimum value is 1. More info: https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle#container-probes",
    )
