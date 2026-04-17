from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class ServerStorageVersion(BaseK8sModel):
    """An API server instance reports the version it can decode and the version it encodes objects to when persisting objects in the backend."""

    api_server_id: str = Field(
        ...,
        alias="apiServerID",
        description="apiServerID is the ID of the reporting API server.",
    )
    decodable_versions: list[str] = Field(
        ...,
        alias="decodableVersions",
        description="decodableVersions are the encoding versions the API server can handle to decode. The API server can decode objects encoded in these versions. The encodingVersion must be included in the decodableVersions.",
    )
    encoding_version: str = Field(
        ...,
        alias="encodingVersion",
        description="encodingVersion the API server encodes the object to when persisting it in the backend (e.g., etcd).",
    )
    served_versions: list[str] | None = Field(
        default=None,
        alias="servedVersions",
        description="servedVersions lists all versions the API server can serve. DecodableVersions must include all ServedVersions.",
    )
