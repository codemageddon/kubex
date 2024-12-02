import typing
from enum import Enum
from pathlib import Path
from time import time

from pydantic import Field, FilePath, HttpUrl, SecretStr

from kubex.models.base import BaseK8sModel


class RawExtension(BaseK8sModel):
    """RawExtension is used to hold extensions in external versions"""

    raw: bytes | None = None
    """Raw is the underlying serialization of this object."""
    object_: dict[str, typing.Any] | None = Field(None, alias="object")
    """Object can hold a representation of this extension - useful for working with versioned
	structs."""


class NamedExtension(BaseK8sModel):
    """NamedExtension holds an extension with name."""

    name: str
    """Name is the name of the extension."""
    extension: typing.Any
    """Extension holds the extension information."""


class Cluster(BaseK8sModel):
    """Cluster contains information about how to communicate with a kubernetes cluster."""

    server: HttpUrl
    """Server is the address of the kubernetes cluster (https://hostname:port)."""
    tls_server_name: str | None = Field(None, alias="tls-server-name")
    """TLSServerName is used to check server certificate. If TLSServerName is empty, the hostname used to contact the server is used."""
    insecure_skip_tls_verify: bool = Field(False, alias="insecure-skip-tls-verify")
    """InsecureSkipTLSVerify skips the validity check for the server's certificate. This will make your HTTPS connections insecure."""
    certificate_authority: FilePath | None = Field(None, alias="certificate-authority")
    """CertificateAuthority is the path to a cert file for the certificate authority."""
    certificate_authority_data: str | None = Field(
        None, alias="certificate-authority-data"
    )
    """CertificateAuthorityData contains PEM-encoded certificate authority certificates. Overrides CertificateAuthority."""
    proxy_url: str | None = Field(None, alias="proxy-url")
    """ProxyURL is the URL to the proxy to be used for all requests made by this client. URLs with "http", "https", and "socks5" schemes are supported. If this configuration is not provided or the empty string, the client attempts to construct a proxy configuration from http_proxy and https_proxy environment variables. If these environment variables are not set, the client does not attempt to proxy requests.
    socks5 proxying does not currently support spdy streaming endpoints (exec, attach, port forward)."""
    disable_compression: bool = Field(False, alias="disable-compression")
    """DisableCompression allows client to opt-out of response compression for all requests to the server. This is useful to speed up requests (specifically lists) when client-server network bandwidth is ample, by saving time on compression (server-side) and decompression (client-side): https://github.com/kubernetes/kubernetes/issues/112296."""
    extensions: list[NamedExtension] | None = None
    """Extensions holds additional information. This is useful for extenders so that reads and writes don't clobber unknown fields."""


class OIDCConfig(BaseK8sModel):
    client_id: SecretStr = Field(alias="client-id")
    """ClientID is the client ID for the OpenID Connect client, as described in https://tools.ietf.org/html/rfc6749#section-2.2."""
    client_secret: SecretStr = Field(alias="client-secret")
    """ClientSecret is the client secret for the OpenID Connect client, as described in https://tools.ietf.org/html/rfc6749#section-2.3."""
    refresh_token: SecretStr = Field(alias="refresh-token")
    """RefreshToken is the refresh token for the OpenID Connect client, as described in https://tools.ietf.org/html/rfc6749#section-6."""
    idp_issuer_url: str = Field(alias="idp-issuer-url")
    """IDPIssuerURL is the URL of the OpenID issuer, only HTTPS scheme will be accepted."""
    idp_certificate_authority_data: str | None = Field(
        None, alias="idp-certificate-authority-data"
    )


class ExecInteractiveMode(str, Enum):
    """ExecInteractiveMode define the interactity of the child process"""

    NEVER = "Never"
    """Never get interactive"""
    IF_AVAILABLE = "IfAvailable"
    """Get interactive if available"""
    ALWAYS = "Always"
    """Always get interactive"""


class ExecConfig(BaseK8sModel):
    """ExecConfig specifies a command to provide client credentials."""

    api_version: (
        typing.Literal[
            "client.authentication.k8s.io/v1beta1", "client.authentication.k8s.io/v1"
        ]
        | None
    ) = Field(None, alias="apiVersion")
    """APIVersion is the version of the API."""
    kind: typing.Literal["ExecCredential"] = "ExecCredential"
    command: str
    """Command to execute."""
    args: list[str] | None = None
    """Args to pass to the command when executing it."""
    env: list[dict[str, str]] | None = None
    """Env defines the environment variables to pass to the command."""
    interactive_mode: ExecInteractiveMode | None = Field(None, alias="interactiveMode")
    provide_cluster_info: bool | None = Field(None, alias="provideClusterInfo")


class AuthProviderConfig(BaseK8sModel):
    """AuthProviderConfig holds the configuration for a custom authentication plugin."""

    name: str
    """Name is the name of the auth provider."""
    config: OIDCConfig | dict[str, str]
    """Config holds the auth provider configuration data."""


class AuthInfo(BaseK8sModel):
    """AuthInfo contains information that describes identity information. This is use to tell the kubernetes cluster who you are."""

    client_certificate: FilePath | None = Field(None, alias="client-certificate")
    """ClientCertificate is the path to a client cert file for TLS."""
    client_certificate_data: str | None = Field(None, alias="client-certificate-data")
    """ClientCertificateData contains PEM-encoded data from a client cert file for TLS. Overrides ClientCertificate."""
    client_key: FilePath | None = Field(None, alias="client-key")
    """ClientKey is the path to a client key file for TLS."""
    client_key_data: str | None = Field(None, alias="client-key-data")
    """ClientKeyData contains PEM-encoded data from a client key file for TLS. Overrides ClientKey."""
    token: str | None = None
    """Token is the bearer token for authentication to the kubernetes cluster."""
    token_file: FilePath | None = Field(None, alias="tokenFile")
    """TokenFile is the path to a file containing the bearer token for authentication to the kubernetes cluster."""
    as_: str | None = Field(None, alias="as")
    """Impersonate is the username to impersonate. The name matches the flag."""
    as_uid: str | None = Field(None, alias="as-uid")
    """ImpersonateUID is the uid to impersonate."""
    as_groups: list[str] | None = Field(None, alias="as-groups")
    """ImpersonateGroups is the groups to impersonate."""
    as_user_extra: dict[str, str] | None = Field(None, alias="as-user-extra")
    """ImpersonateUserExtra contains additional information for impersonated user."""
    auth_provider: AuthProviderConfig | None = Field(None, alias="auth-provider")
    """AuthProvider specifies a custom authentication plugin for the kubernetes cluster."""
    exec: dict[str, str] | None = None


class Context(BaseK8sModel):
    """Context holds user values, cluster values, and extension values."""

    cluster: str
    """Cluster is the name of the cluster for this context."""
    user: str
    """User is the name of the user for this context."""
    namespace: str | None = None
    """Namespace is the default namespace to use on unspecified requests."""
    extensions: list[NamedExtension] | None = None
    """Extensions holds additional information. This is useful for extenders so that reads and writes don't clobber unknown fields."""


class NamedClaster(BaseK8sModel):
    """NamedCluster holds a cluster with name."""

    name: str
    """Name is the name of the cluster."""
    cluster: Cluster
    """Cluster holds the cluster information."""


class NamedAuthInfo(BaseK8sModel):
    """NamedAuthInfo holds an AuthInfo with name."""

    name: str
    """Name is the name of the auth"""
    auth_info: AuthInfo = Field(alias="user")
    """AuthInfo holds the auth info."""


class NamedContext(BaseK8sModel):
    """NamedContext holds a context with name."""

    name: str
    """Name is the name of the context."""
    context: Context
    """Context holds the context information."""


class KubeConfig(BaseK8sModel):
    """Config holds the information needed to build connect to remote kubernetes clusters as a given user."""

    api_version: typing.Literal["v1"] = "v1"
    kind: typing.Literal["Config"] = "Config"
    clusters: list[NamedClaster] = Field(default_factory=list)
    """Clusters is a map of referencable names to cluster configs."""
    users: list[NamedAuthInfo] = Field(default_factory=list)
    """AuthInfos is a map of referencable names to user configs."""
    contexts: list[NamedContext] = Field(default_factory=list)
    """Contexts is a map of referencable names to context configs."""
    current_context: str | None = Field(None, alias="current-context")
    """CurrentContext is the name of the context that you would like to use by default."""


TOKEN_REFRRESH_INTERVAL = 60


class ClientConfiguration:
    def __init__(
        self,
        url: str | None = None,
        server_ca_file: Path | str | None = None,
        insecure_skip_tls_verify: bool | None = None,
        client_cert_file: Path | str | None = None,
        client_key_file: Path | str | None = None,
        token_file: Path | str | None = None,
        token: str | None = None,
        namespace: str | None = None,
        try_refresh_token: bool = False,
        log_api_warnings: bool = True,
    ) -> None:
        if try_refresh_token and token_file is None:
            raise ValueError("Token file must be provided to refresh token")
        self.base_url = url
        if insecure_skip_tls_verify is False:
            if server_ca_file is None:
                raise ValueError("Server CA file must be provided")
        self.insecure_skip_tls_verify = insecure_skip_tls_verify
        if isinstance(server_ca_file, str):
            server_ca_file = Path(server_ca_file)
        self.server_ca_file = server_ca_file
        if isinstance(client_cert_file, str):
            client_cert_file = Path(client_cert_file)
        self.client_cert_file = client_cert_file
        if isinstance(client_key_file, str):
            client_key_file = Path(client_key_file)
        self.client_key_file = client_key_file
        self.namespace = namespace or "default"
        self.log_api_warnings = log_api_warnings

        if isinstance(token_file, str):
            token_file = Path(token_file)

        self.token_file = token_file
        self.try_refresh_token = try_refresh_token
        self._last_token_read: float | None = None
        self._current_token: str | None = None
        self._token = token

    @property
    def verify(self) -> bool | str | None:
        if self.insecure_skip_tls_verify:
            return False
        if self.server_ca_file is None:
            return None
        return str(self.server_ca_file)

    @property
    def client_cert(self) -> tuple[str, str | None] | None:
        if self.client_cert_file is None:
            return None
        return str(self.client_cert_file), str(
            self.client_key_file
        ) if self.client_key_file is not None else None

    @property
    def token(self) -> str | None:
        if self._token is None and self.token_file is None:
            return None

        if self._token is not None:
            return self._token

        if (
            self._current_token is None
            or self._last_token_read is None
            or time() - self._last_token_read < TOKEN_REFRRESH_INTERVAL
        ):
            self._current_token = self.token_file.read_text().strip()  # type: ignore[union-attr]
            self._last_token_read = time()
        return self._current_token
