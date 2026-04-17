from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class ClientIPConfig(BaseK8sModel):
    """ClientIPConfig represents the configurations of Client IP based session affinity."""

    timeout_seconds: int | None = Field(
        default=None,
        alias="timeoutSeconds",
        description='timeoutSeconds specifies the seconds of ClientIP type session sticky time. The value must be >0 && <=86400(for 1 day) if ServiceAffinity == "ClientIP". Default value is 10800(for 3 hours).',
    )
