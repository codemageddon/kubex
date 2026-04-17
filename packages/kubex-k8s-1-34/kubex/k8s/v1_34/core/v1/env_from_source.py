from kubex.k8s.v1_34.core.v1.config_map_env_source import ConfigMapEnvSource
from kubex.k8s.v1_34.core.v1.secret_env_source import SecretEnvSource
from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class EnvFromSource(BaseK8sModel):
    """EnvFromSource represents the source of a set of ConfigMaps or Secrets"""

    config_map_ref: ConfigMapEnvSource | None = Field(
        default=None, alias="configMapRef", description="The ConfigMap to select from"
    )
    prefix: str | None = Field(
        default=None,
        alias="prefix",
        description="Optional text to prepend to the name of each environment variable. May consist of any printable ASCII characters except '='.",
    )
    secret_ref: SecretEnvSource | None = Field(
        default=None, alias="secretRef", description="The Secret to select from"
    )
