# Authentication

Kubex supports three authentication methods: kubeconfig files, in-cluster service account tokens, and exec-provider/OIDC credentials. Configuration is represented by `ClientConfiguration` and loaded by one of two async factory functions.

## Auto-detection

`create_client()` calls `configure_from_kubeconfig()` first. If the kubeconfig file is not found, it falls back to `configure_from_pod_env()`. Other kubeconfig errors (malformed file, missing context, permission denied, etc.) are propagated to the caller:

```python
from kubex.client import create_client

async with await create_client() as client:
    # automatically picked kubeconfig or in-cluster config
    ...
```

To skip auto-detection and supply configuration explicitly, pass a `ClientConfiguration` directly:

```python
from kubex.client import create_client
from kubex.configuration import ClientConfiguration

config = ClientConfiguration(
    url="https://my-cluster:6443",
    token="my-bearer-token",
)
async with await create_client(configuration=config) as client:
    ...
```

## Kubeconfig file

`configure_from_kubeconfig()` reads the file at `~/.kube/config` by default, or the path from the `KUBECONFIG` environment variable.

```python
from kubex.client import create_client
from kubex.configuration.file_config import configure_from_kubeconfig

config = await configure_from_kubeconfig()
async with await create_client(configuration=config) as client:
    ...
```

To load a specific file or context, pass `config_file=` and/or `use_context=`:

```python
from kubex.configuration.file_config import configure_from_kubeconfig

config = await configure_from_kubeconfig(
    config_file="/path/to/kubeconfig", use_context="staging"
)
```

As with `kubectl`, relative file paths inside the kubeconfig (`certificate-authority`,
`client-certificate`, `client-key`, `tokenFile`, the oidc `idp-certificate-authority`, and an
exec `command` that contains a path separator) are resolved against the kubeconfig file's
directory. You can also pass an already-parsed `KubeConfig` as `config=`, but then relative paths
are used as-is (relative to the current directory).

Kubeconfig supports:
- Bearer token (`users[].user.token`)
- Token file (`users[].user.tokenFile`)
- Basic auth (`users[].user.username` / `password`), used when no token source is set
- Client certificate + key (`users[].user.client-certificate` / `client-key`)
- Inline base64 data (`certificate-authority-data`, `client-certificate-data`,
  `client-key-data`), decoded to private temp files; a `*-data` field overrides the matching
  file path, as in client-go
- Impersonation (`users[].user.as`, `as-uid`, `as-groups`, `as-user-extra`), sent as
  `Impersonate-*` headers on every request
- Exec provider (see below)
- OIDC, `auth-provider: oidc` only (see below)
- `clusters[].cluster.tls-server-name` (the name the server certificate is verified against,
  instead of the host in `server`)
- `clusters[].cluster.insecure-skip-tls-verify` (forwarded only when `true`; a cluster that
  omits it keeps kubex's normal system-trust-store/explicit-CA behavior)
- A context `namespace`; a context without one uses `default`, like `kubectl`

Only the selected context's cluster and user are checked, so a stale entry for another context
(e.g. a deleted minikube profile) does not break loading. For the selected one, a referenced file
that does not exist raises `ConfigurationError` naming the field and path, and a `server` without
a scheme (`10.0.0.1:6443`) is treated as `https://`. Validation errors never echo kubeconfig
values, so tokens and keys do not end up in logs.

A context whose user sets `auth-provider:` to anything other than `oidc`, or an `oidc`
`auth-provider` block that fails to validate, raises `ConfigurationError` rather than
silently returning an unauthenticated client.

`clusters[].cluster.proxy-url` is read but **not** applied — it belongs on `ClientOptions.proxy`,
which `configure_from_kubeconfig()` has no access to (it only builds a `ClientConfiguration`). A
cluster that sets it emits a `UserWarning`; pass the equivalent proxy via
`ClientOptions(proxy=...)` when constructing the client yourself.

## In-cluster (pod environment)

When your code runs inside a Kubernetes pod with a service account mounted, use `configure_from_pod_env()`:

```python
from kubex.client import create_client
from kubex.configuration.incluster_config import configure_from_pod_env

config = await configure_from_pod_env()
async with await create_client(configuration=config) as client:
    ...
```

This reads:
- Token: `/var/run/secrets/kubernetes.io/serviceaccount/token`
- CA certificate: `/var/run/secrets/kubernetes.io/serviceaccount/ca.crt`
- Namespace: `/var/run/secrets/kubernetes.io/serviceaccount/namespace` (`default` if the file is
  absent)
- Server URL: from `KUBERNETES_SERVICE_HOST` and `KUBERNETES_SERVICE_PORT` environment variables
  (IPv6 hosts are bracketed). If either is unset, `ConfigurationError` is raised: the process is
  not running inside a cluster.

Token auto-refresh is enabled by default (`try_refresh_token=True`). The token is re-read from disk every 60 seconds, which matches the default rotation window used by Kubernetes projected volume tokens.

## Exec provider

Exec provider authentication runs an external command to obtain a bearer token — the standard
mechanism for cloud-provider CLI tools (AWS, GCP, Azure) and other external credential sources.
The exec provider config lives in the kubeconfig `users[].user.exec` block:

```yaml
users:
- name: my-user
  user:
    exec:
      apiVersion: client.authentication.k8s.io/v1
      command: aws
      args:
      - eks
      - get-token
      - --cluster-name
      - my-cluster
```

`configure_from_kubeconfig()` resolves this block: it wraps `ExecAuthProvider` (which runs the
command and parses the `ExecCredential` JSON it prints) in an `ExecRefreshableToken` and stores it
on `ClientConfiguration.refreshable_token`. Both HTTP backends call
`ClientConfiguration.get_authorization_header()` on every request, which awaits
`ExecRefreshableToken.to_header()` — the exec command re-runs when the cached token is within
10 seconds of the plugin's `expirationTimestamp`, or every 60 seconds if it reports none.

- The plugin's stderr is passed through to your process's stderr as it runs, so login prompts and
  device-code instructions reach the user. On a non-zero exit, the tail of that stderr is included
  in the raised error.
- `interactiveMode` defaults to `IfAvailable`. The plugin gets your stdin only when running
  interactively (stdin is a terminal); otherwise its stdin is empty.
- A `command` containing a path separator (`./bin/get-token`) is resolved against the kubeconfig
  file's directory; a bare name (`aws`) is looked up on `PATH`.
- `provideClusterInfo: true` passes the cluster's `server`, `certificate-authority-data`,
  `tls-server-name`, `insecure-skip-tls-verify`, `proxy-url` and its
  `client.authentication.k8s.io/exec` extension (as `config`) to the plugin in
  `KUBERNETES_EXEC_INFO`.
- Only token credentials are supported. A plugin that returns a client certificate
  (`clientCertificateData`/`clientKeyData`) raises `ConfigurationError`.

## OIDC

OIDC (`auth-provider: oidc`) is resolved the same way: `configure_from_kubeconfig()` wraps
`OIDCAuthProvider` in an `OidcRefreshableToken`. Only `auth-provider: oidc` is supported — any
other `auth-provider` name raises `ConfigurationError`.

As in client-go, the configured `id-token` is used until its `exp` claim is reached; only then is
the `refresh-token` redeemed at the issuer's token endpoint, and the new id_token is used until
its own `exp`. `client-secret` and `refresh-token` are optional (public clients, or an id-token
kept fresh by another tool); with neither a valid id-token nor a refresh token, requests fail with
`ConfigurationError`. The issuer's TLS certificate is verified against
`idp-certificate-authority-data` or the `idp-certificate-authority` file when set.

If the identity provider rotates refresh tokens (e.g. Auth0, Okta, or Keycloak with rotation
enabled), a fresh refresh token issued during a kubex refresh is kept only in memory for the
life of the process — it is **not** written back to the kubeconfig file on disk. The on-disk
refresh token is therefore invalidated by the first refresh; a fresh process (or a concurrent
`kubectl` invocation reading the same kubeconfig) will need to re-authenticate interactively
once that has happened. Identity providers that do not rotate refresh tokens for the client type
in use (e.g. Google's OAuth for installed applications) are unaffected.

## Manual `ClientConfiguration`

For programmatic or testing use cases, construct `ClientConfiguration` directly:

```python
from kubex.configuration import ClientConfiguration

# Bearer token
config = ClientConfiguration(
    url="https://my-cluster:6443",
    server_ca_file="/path/to/ca.crt",
    token="eyJhbGciOiJSUzI1NiIs...",
)

# Client certificate
config = ClientConfiguration(
    url="https://my-cluster:6443",
    server_ca_file="/path/to/ca.crt",
    client_cert_file="/path/to/client.crt",
    client_key_file="/path/to/client.key",
)

# Skip TLS verification (not recommended for production)
config = ClientConfiguration(
    url="https://my-cluster:6443",
    insecure_skip_tls_verify=True,
    token="my-token",
)

# Basic auth, impersonation, and a TLS server name different from the URL host
config = ClientConfiguration(
    url="https://10.0.0.1:6443",
    server_ca_file="/path/to/ca.crt",
    tls_server_name="kubernetes.default.svc",
    username="admin",
    password="s3cret",
    impersonate_user="jane",
    impersonate_groups=["developers"],
)
```

The `namespace` parameter is populated by `configure_from_kubeconfig()` from the selected
context's `namespace` (`default` when unset) and by `configure_from_pod_env()` from the pod's
service-account namespace file. `Api`/`create_api()` fall back to it when a **namespace-scoped**
resource is created without an explicit `namespace=` argument — so omitting the namespace scopes
`get()`/`create()`/`list()`/`watch()` to the configured namespace (as `kubectl` does), rather than
"all namespaces". Pass `namespace=None` explicitly to opt back into all-namespaces behavior, or a
specific string to target a different namespace. Cluster-scoped resources never receive a
namespace, configured or not.
