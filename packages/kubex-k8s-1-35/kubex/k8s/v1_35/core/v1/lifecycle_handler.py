from kubex.k8s.v1_35.core.v1.exec_action import ExecAction
from kubex.k8s.v1_35.core.v1.http_get_action import HTTPGetAction
from kubex.k8s.v1_35.core.v1.sleep_action import SleepAction
from kubex.k8s.v1_35.core.v1.tcp_socket_action import TCPSocketAction
from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class LifecycleHandler(BaseK8sModel):
    """LifecycleHandler defines a specific action that should be taken in a lifecycle hook. One and only one of the fields, except TCPSocket must be specified."""

    exec: ExecAction | None = Field(
        default=None,
        alias="exec",
        description="Exec specifies a command to execute in the container.",
    )
    http_get: HTTPGetAction | None = Field(
        default=None,
        alias="httpGet",
        description="HTTPGet specifies an HTTP GET request to perform.",
    )
    sleep: SleepAction | None = Field(
        default=None,
        alias="sleep",
        description="Sleep represents a duration that the container should sleep.",
    )
    tcp_socket: TCPSocketAction | None = Field(
        default=None,
        alias="tcpSocket",
        description="Deprecated. TCPSocket is NOT supported as a LifecycleHandler and kept for backward compatibility. There is no validation of this field and lifecycle hooks will fail at runtime when it is specified.",
    )
