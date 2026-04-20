from pydantic import Field

from kubex.k8s.v1_32.core.v1.config_map_env_source import ConfigMapEnvSource
from kubex.k8s.v1_32.core.v1.secret_env_source import SecretEnvSource
from kubex_core.models.base import BaseK8sModel


class EnvFromSource(BaseK8sModel):
    """EnvFromSource represents the source of a set of ConfigMaps"""

    config_map_ref: ConfigMapEnvSource | None = Field(
        default=None, alias="configMapRef", description="The ConfigMap to select from"
    )
    prefix: str | None = Field(
        default=None,
        alias="prefix",
        description="An optional identifier to prepend to each key in the ConfigMap. Must be a C_IDENTIFIER.",
    )
    secret_ref: SecretEnvSource | None = Field(
        default=None, alias="secretRef", description="The Secret to select from"
    )
