import base64
import logging
import typing
from enum import Enum
from pathlib import Path
from time import time

from pydantic import (
    BeforeValidator,
    ConfigDict,
    Field,
    SecretStr,
    ValidationError,
    field_validator,
)

from kubex_core.models.base import BaseK8sModel


class ConfigModel(BaseK8sModel):
    """Base for kubeconfig / credential-plugin models.

    Unlike resource models, unknown keys are dropped: nothing round-trips
    them, and keeping them would surface unexpected (possibly secret)
    kubeconfig content in reprs.
    """

    model_config = ConfigDict(extra="ignore")


class SupportsAuthorizationHeader(typing.Protocol):
    """Structural type for a token source that can format its own Authorization header"""

    async def to_header(self) -> str: ...


def _format_location(loc: tuple[int | str, ...], data: typing.Any) -> str:
    """Render a pydantic error location, naming list items by their `name` key."""
    rendered = ""
    node = data
    for part in loc:
        if isinstance(part, int):
            name = None
            if isinstance(node, list) and 0 <= part < len(node):
                node = node[part]
                if isinstance(node, dict) and isinstance(node.get("name"), str):
                    name = node["name"]
            else:
                node = None
            rendered += f"[{name!r}]" if name is not None else f"[{part}]"
        else:
            node = node.get(part) if isinstance(node, dict) else None
            rendered += f".{part}" if rendered else part
    return rendered or "<root>"


def describe_validation_error(exc: ValidationError, data: typing.Any = None) -> str:
    """Summarise ``exc`` by error locations and types only.

    pydantic's own message embeds the offending input, which for kubeconfig
    and exec-plugin data can be a credential. Pass the validated ``data`` to
    name list entries (e.g. ``users['dev']``) instead of numbering them.
    """
    details = [
        f"{_format_location(error['loc'], data)} ({error['type']})"
        for error in exc.errors(include_url=False, include_input=False)
    ]
    return f"{exc.error_count()} validation error(s): {', '.join(details)}"


def _blank_to_none(value: typing.Any) -> typing.Any:
    # kubeconfig writers emit `""` for unset string fields; client-go treats
    # an empty path or server as unset.
    return None if value == "" else value


def _scalar_to_str(value: typing.Any) -> typing.Any:
    # Unquoted YAML credentials (`password: 123456`) parse as numbers; accept
    # them so one such entry (even for an unused context) doesn't fail the
    # whole kubeconfig. Values YAML rewrites (leading zeros) still need quotes.
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return str(value)
    return value


_OptionalStr = typing.Annotated[str | None, BeforeValidator(_blank_to_none)]
_OptionalPath = typing.Annotated[Path | None, BeforeValidator(_blank_to_none)]
_CredentialStr = typing.Annotated[str | None, BeforeValidator(_scalar_to_str)]
_CredentialSecret = typing.Annotated[SecretStr | None, BeforeValidator(_scalar_to_str)]


class RawExtension(ConfigModel):
    """RawExtension is used to hold extensions in external versions"""

    raw: bytes | None = None
    """Raw is the underlying serialization of this object."""
    object_: dict[str, typing.Any] | None = Field(None, alias="object")
    """Object can hold a representation of this extension - useful for working with versioned
	structs."""


class NamedExtension(ConfigModel):
    """NamedExtension holds an extension with name."""

    name: str
    """Name is the name of the extension."""
    extension: typing.Any = None
    """Extension holds the extension information."""


class Cluster(ConfigModel):
    """Cluster contains information about how to communicate with a kubernetes cluster.

    Fields are validated leniently so that one stale entry does not break
    loading the whole kubeconfig; `configure_from_kubeconfig()` checks the
    selected context's cluster (server URL, referenced files) when it is used.
    """

    server: _OptionalStr = None
    """Server is the address of the kubernetes cluster (https://hostname:port). A value without a scheme is treated as `https://`."""
    tls_server_name: str | None = Field(None, alias="tls-server-name")
    """TLSServerName is used to check server certificate. If TLSServerName is empty, the hostname used to contact the server is used."""
    insecure_skip_tls_verify: bool = Field(False, alias="insecure-skip-tls-verify")
    """InsecureSkipTLSVerify skips the validity check for the server's certificate. This will make your HTTPS connections insecure."""
    certificate_authority: _OptionalPath = Field(None, alias="certificate-authority")
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


class OIDCConfig(ConfigModel):
    client_id: SecretStr = Field(alias="client-id")
    """ClientID is the client ID for the OpenID Connect client, as described in https://tools.ietf.org/html/rfc6749#section-2.2."""
    client_secret: SecretStr | None = Field(None, alias="client-secret")
    """ClientSecret is the client secret for the OpenID Connect client, as described in https://tools.ietf.org/html/rfc6749#section-2.3. Omitted for public clients."""
    refresh_token: SecretStr | None = Field(None, alias="refresh-token")
    """RefreshToken is the refresh token for the OpenID Connect client, as described in https://tools.ietf.org/html/rfc6749#section-6. Redeemed only when `id-token` is missing or expired."""
    id_token: SecretStr | None = Field(None, alias="id-token")
    """IDToken is the current id_token; used as-is until its `exp` claim is reached."""
    idp_issuer_url: str = Field(alias="idp-issuer-url")
    """IDPIssuerURL is the URL of the OpenID issuer, only HTTPS scheme will be accepted."""
    idp_certificate_authority: _OptionalPath = Field(
        None, alias="idp-certificate-authority"
    )
    """Path to a CA bundle for the issuer's TLS certificate. Relative to the kubeconfig file's directory."""
    idp_certificate_authority_data: str | None = Field(
        None, alias="idp-certificate-authority-data"
    )
    """Base64-encoded CA bundle for the issuer's TLS certificate. Overrides `idp-certificate-authority`."""

    @field_validator("idp_issuer_url")
    @classmethod
    def _idp_issuer_url_must_be_https(cls, value: str) -> str:
        if not value.startswith("https://"):
            raise ValueError(f"idp-issuer-url must use the https scheme, got {value!r}")
        return value


class ExecInteractiveMode(str, Enum):
    """ExecInteractiveMode define the interactity of the child process"""

    NEVER = "Never"
    """Never get interactive"""
    IF_AVAILABLE = "IfAvailable"
    """Get interactive if available"""
    ALWAYS = "Always"
    """Always get interactive"""


class ExecConfig(ConfigModel):
    """ExecConfig specifies a command to provide client credentials."""

    api_version: str | None = Field(None, alias="apiVersion")
    """APIVersion is the version of the API: `client.authentication.k8s.io/v1` or `client.authentication.k8s.io/v1beta1`."""
    kind: typing.Literal["ExecCredential"] = "ExecCredential"
    command: str = ""
    """Command to execute. A relative path containing a path separator is resolved against the kubeconfig file's directory; a bare name is looked up on PATH."""
    args: list[str] | None = Field(None, repr=False)
    """Args to pass to the command when executing it."""
    env: list[dict[str, str]] | None = Field(None, repr=False)
    """Env defines the environment variables to pass to the command."""
    install_hint: str | None = Field(None, alias="installHint")
    """InstallHint is shown to the user when the command cannot be found."""
    interactive_mode: ExecInteractiveMode | None = Field(None, alias="interactiveMode")
    """InteractiveMode controls whether the plugin's stdin is connected; unset means `IfAvailable`."""
    provide_cluster_info: bool | None = Field(None, alias="provideClusterInfo")
    """ProvideClusterInfo passes the cluster's connection details to the plugin in `KUBERNETES_EXEC_INFO`."""


class AuthProviderConfig(ConfigModel):
    """AuthProviderConfig holds the configuration for a custom authentication plugin."""

    name: str
    """Name is the name of the auth provider."""
    config: OIDCConfig | dict[str, str] = Field(
        default_factory=dict[str, str], repr=False
    )
    """Config holds the auth provider configuration data."""


class AuthInfo(ConfigModel):
    """AuthInfo contains information that describes identity information. This is use to tell the kubernetes cluster who you are."""

    client_certificate: _OptionalPath = Field(None, alias="client-certificate")
    """ClientCertificate is the path to a client cert file for TLS."""
    client_certificate_data: str | None = Field(None, alias="client-certificate-data")
    """ClientCertificateData contains PEM-encoded data from a client cert file for TLS. Overrides ClientCertificate."""
    client_key: _OptionalPath = Field(None, alias="client-key")
    """ClientKey is the path to a client key file for TLS."""
    client_key_data: str | None = Field(None, alias="client-key-data", repr=False)
    """ClientKeyData contains PEM-encoded data from a client key file for TLS. Overrides ClientKey."""
    token: _CredentialStr = Field(None, repr=False)
    """Token is the bearer token for authentication to the kubernetes cluster."""
    token_file: _OptionalPath = Field(None, alias="tokenFile")
    """TokenFile is the path to a file containing the bearer token for authentication to the kubernetes cluster."""
    username: _CredentialStr = None
    """Username is the username for basic authentication to the kubernetes cluster."""
    password: _CredentialSecret = None
    """Password is the password for basic authentication to the kubernetes cluster."""
    as_: str | None = Field(None, alias="as")
    """Impersonate is the username to impersonate. The name matches the flag."""
    as_uid: str | None = Field(None, alias="as-uid")
    """ImpersonateUID is the uid to impersonate."""
    as_groups: list[str] | None = Field(None, alias="as-groups")
    """ImpersonateGroups is the groups to impersonate."""
    as_user_extra: dict[str, list[str]] | None = Field(None, alias="as-user-extra")
    """ImpersonateUserExtra contains additional information for impersonated user."""
    auth_provider: AuthProviderConfig | None = Field(None, alias="auth-provider")
    """AuthProvider specifies a custom authentication plugin for the kubernetes cluster."""
    exec: ExecConfig | None = None


class Context(ConfigModel):
    """Context holds user values, cluster values, and extension values."""

    cluster: str | None = None
    """Cluster is the name of the cluster for this context."""
    user: str | None = None
    """User is the name of the user for this context. Unset means anonymous access."""
    namespace: str | None = None
    """Namespace is the default namespace to use on unspecified requests."""
    extensions: list[NamedExtension] | None = None
    """Extensions holds additional information. This is useful for extenders so that reads and writes don't clobber unknown fields."""


class NamedClaster(ConfigModel):
    """NamedCluster holds a cluster with name."""

    name: str
    """Name is the name of the cluster."""
    cluster: Cluster = Field(default_factory=Cluster)
    """Cluster holds the cluster information."""


class NamedAuthInfo(ConfigModel):
    """NamedAuthInfo holds an AuthInfo with name."""

    name: str
    """Name is the name of the auth"""
    auth_info: AuthInfo = Field(default_factory=AuthInfo, alias="user")
    """AuthInfo holds the auth info."""


class NamedContext(ConfigModel):
    """NamedContext holds a context with name."""

    name: str
    """Name is the name of the context."""
    context: Context = Field(default_factory=Context)
    """Context holds the context information."""


class KubeConfig(ConfigModel):
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


TOKEN_REFRESH_INTERVAL = 60

_logger = logging.getLogger("kubex.configuration")

# RFC 7230 `tchar` set: bytes allowed verbatim in an HTTP header name.
_HEADER_TOKEN_BYTES = frozenset(
    b"!#$&'*+-.^_`|~0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
)


def _escape_header_key(key: str) -> str:
    """Percent-encode an `Impersonate-Extra-` key the way client-go does.

    Every byte that is not a header `tchar` (and `%` itself) is encoded, so
    the API server can recover the original key with a path-unescape.
    """
    return "".join(
        chr(b) if b in _HEADER_TOKEN_BYTES else f"%{b:02X}" for b in key.encode()
    )


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
        refreshable_token: SupportsAuthorizationHeader | None = None,
        tls_server_name: str | None = None,
        username: str | None = None,
        password: str | None = None,
        impersonate_user: str | None = None,
        impersonate_uid: str | None = None,
        impersonate_groups: typing.Sequence[str] | None = None,
        impersonate_extra: typing.Mapping[str, typing.Sequence[str]] | None = None,
    ) -> None:
        """Connection and credential settings for a client.

        Args:
            tls_server_name: Name to verify the server certificate against (and
                send as SNI) instead of the hostname in ``url``; kubeconfig's
                ``tls-server-name``.
            username: Basic-auth username; used only when no token source is set.
            password: Basic-auth password.
            impersonate_user: Username to act as (``Impersonate-User``).
            impersonate_uid: UID to act as (``Impersonate-Uid``).
            impersonate_groups: Groups to act as (one ``Impersonate-Group`` each).
            impersonate_extra: Extra user info to act with
                (``Impersonate-Extra-<key>``, one header per value).
        """
        if try_refresh_token and token_file is None:
            raise ValueError("Token file must be provided to refresh token")
        self.refreshable_token = refreshable_token
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
        self.namespace = namespace

        if isinstance(token_file, str):
            token_file = Path(token_file)

        self.token_file = token_file
        self.try_refresh_token = try_refresh_token
        self._last_token_read: float | None = None
        self._current_token: str | None = None
        self._token = token
        self.tls_server_name = tls_server_name or None
        if (username is None) != (password is None):
            raise ValueError("username and password must be provided together")
        self.username = username
        self._password = password
        if impersonate_user is None and (impersonate_groups or impersonate_extra):
            # The API server rejects group/extra impersonation without a user.
            raise ValueError(
                "impersonate_groups/impersonate_extra require impersonate_user"
            )
        self.impersonate_user = impersonate_user
        self.impersonate_uid = impersonate_uid
        self.impersonate_groups: tuple[str, ...] = tuple(impersonate_groups or ())
        self.impersonate_extra: dict[str, tuple[str, ...]] = {
            key: tuple(values) for key, values in (impersonate_extra or {}).items()
        }

    @property
    def impersonation_headers(self) -> list[tuple[str, str]]:
        """``Impersonate-*`` headers to send on every request (possibly repeated)."""
        headers: list[tuple[str, str]] = []
        if self.impersonate_user is not None:
            headers.append(("Impersonate-User", self.impersonate_user))
        if self.impersonate_uid is not None:
            headers.append(("Impersonate-Uid", self.impersonate_uid))
        headers.extend(
            ("Impersonate-Group", group) for group in self.impersonate_groups
        )
        for key, values in self.impersonate_extra.items():
            name = f"Impersonate-Extra-{_escape_header_key(key)}"
            headers.extend((name, value) for value in values)
        return headers

    @property
    def verify(self) -> bool | str | None:
        if self.insecure_skip_tls_verify:
            return False
        if self.server_ca_file is None:
            return None
        return str(self.server_ca_file)

    @property
    def client_cert(self) -> tuple[str, str] | str | None:
        if self.client_cert_file is None:
            return None
        if self.client_key_file is not None:
            return str(self.client_cert_file), str(self.client_key_file)
        return str(self.client_cert_file)

    @property
    def token(self) -> str | None:
        """The bearer token to send.

        As in client-go, the last successfully read, non-empty `token_file`
        content wins over `token`, which is the fallback until the file has been
        read. A failed read raises only when there is nothing to fall back to.
        """
        if self.token_file is None:
            return self._token

        is_expired = (
            self._last_token_read is None
            or time() - self._last_token_read > TOKEN_REFRESH_INTERVAL
        )
        if self._current_token is None or (self.try_refresh_token and is_expired):
            try:
                content = self.token_file.read_text().strip()
            except OSError as exc:
                if self._current_token is None and self._token is None:
                    raise
                _logger.debug("Failed to read token file %s: %s", self.token_file, exc)
            else:
                self._last_token_read = time()
                if content or (self._current_token is None and self._token is None):
                    self._current_token = content
        if self._current_token is not None:
            return self._current_token
        return self._token

    async def get_authorization_header(self) -> str | None:
        """Return the `Authorization` header value to send, if any.

        Prefers `refreshable_token` (exec/OIDC credential plugins) over the
        static `token`/`token_file` path, since a kubeconfig context only
        ever sets one credential source.
        """
        if self.refreshable_token is not None:
            return await self.refreshable_token.to_header()
        token = self.token
        if token is not None:
            return f"Bearer {token}"
        if self.username is not None and self._password is not None:
            credentials = f"{self.username}:{self._password}".encode()
            return f"Basic {base64.b64encode(credentials).decode('ascii')}"
        return None
