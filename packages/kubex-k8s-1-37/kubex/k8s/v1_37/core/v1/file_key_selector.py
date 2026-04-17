from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class FileKeySelector(BaseK8sModel):
    """FileKeySelector selects a key of the env file."""

    key: str = Field(
        ...,
        alias="key",
        description="The key within the env file. An invalid key will prevent the pod from starting. The keys defined within a source may consist of any printable ASCII characters except '='. During Alpha stage of the EnvFiles feature gate, the key size is limited to 128 characters.",
    )
    optional: bool | None = Field(
        default=None,
        alias="optional",
        description="Specify whether the file or its key must be defined. If the file or key does not exist, then the env var is not published. If optional is set to true and the specified key does not exist, the environment variable will not be set in the Pod's containers. If optional is set to false and the specified key does not exist, an error will be returned during Pod creation.",
    )
    path: str = Field(
        ...,
        alias="path",
        description="The path within the volume from which to select the file. Must be relative and may not contain the '..' path or start with '..'.",
    )
    volume_name: str = Field(
        ...,
        alias="volumeName",
        description="The name of the volume mount containing the env file.",
    )
