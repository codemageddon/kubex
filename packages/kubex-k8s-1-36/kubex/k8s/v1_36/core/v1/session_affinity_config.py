from kubex.k8s.v1_36.core.v1.client_ip_config import ClientIPConfig
from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class SessionAffinityConfig(BaseK8sModel):
    """SessionAffinityConfig represents the configurations of session affinity."""

    client_ip: ClientIPConfig | None = Field(
        default=None,
        alias="clientIP",
        description="clientIP contains the configurations of Client IP based session affinity.",
    )
