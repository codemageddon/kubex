from pydantic import Field

from kubex.k8s.v1_35.apps.v1.rolling_update_daemon_set import RollingUpdateDaemonSet
from kubex_core.models.base import BaseK8sModel


class DaemonSetUpdateStrategy(BaseK8sModel):
    """DaemonSetUpdateStrategy is a struct used to control the update strategy for a DaemonSet."""

    rolling_update: RollingUpdateDaemonSet | None = Field(
        default=None,
        alias="rollingUpdate",
        description='Rolling update config params. Present only if type = "RollingUpdate".',
    )
    type_: str | None = Field(
        default=None,
        alias="type",
        description='Type of daemon set update. Can be "RollingUpdate" or "OnDelete". Default is RollingUpdate.',
    )
