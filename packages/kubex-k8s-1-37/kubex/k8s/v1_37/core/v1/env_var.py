from pydantic import Field

from kubex.k8s.v1_37.core.v1.env_var_source import EnvVarSource
from kubex_core.models.base import BaseK8sModel


class EnvVar(BaseK8sModel):
    """EnvVar represents an environment variable present in a Container."""

    name: str = Field(
        ...,
        alias="name",
        description="Name of the environment variable. May consist of any printable ASCII characters except '='.",
    )
    value: str | None = Field(
        default=None,
        alias="value",
        description='Variable references $(VAR_NAME) are expanded using the previously defined environment variables in the container and any service environment variables. If a variable cannot be resolved, the reference in the input string will be unchanged. Double $$ are reduced to a single $, which allows for escaping the $(VAR_NAME) syntax: i.e. "$$(VAR_NAME)" will produce the string literal "$(VAR_NAME)". Escaped references will never be expanded, regardless of whether the variable exists or not. Defaults to "".',
    )
    value_from: EnvVarSource | None = Field(
        default=None,
        alias="valueFrom",
        description="Source for the environment variable's value. Cannot be used if value is not empty.",
    )
