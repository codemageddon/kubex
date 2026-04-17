from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class ServerStorageVersion(BaseK8sModel):
    """An API server instance reports the version it can decode and the version it encodes objects to when persisting objects in the backend."""

    api_server_id: str | None = Field(
        default=None,
        alias="apiServerID",
        description="The ID of the reporting API server.",
    )
    decodable_versions: list[str] | None = Field(
        default=None,
        alias="decodableVersions",
        description="The API server can decode objects encoded in these versions. The encodingVersion must be included in the decodableVersions.",
    )
    encoding_version: str | None = Field(
        default=None,
        alias="encodingVersion",
        description="The API server encodes the object to this version when persisting it in the backend (e.g., etcd).",
    )
    served_versions: list[str] | None = Field(
        default=None,
        alias="servedVersions",
        description="The API server can serve these versions. DecodableVersions must include all ServedVersions.",
    )
