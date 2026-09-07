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

To load a specific file or context:

```python
from kubex.configuration.configuration import KubeConfig
from kubex.configuration.file_config import configure_from_kubeconfig
from pathlib import Path
from yaml import safe_load

raw = safe_load(Path("/path/to/kubeconfig").read_text())
kube_config = KubeConfig.model_validate(raw)
config = await configure_from_kubeconfig(config=kube_config, use_context="staging")
```

Kubeconfig supports:
- Bearer token (`users[].user.token`)
- Token file (`users[].user.tokenFile`)
- Client certificate + key (`users[].user.client-certificate` / `client-key`)
- Inline base64 certificate data (decoded to temp files automatically)
- Exec provider (see below)
- OIDC, `auth-provider: oidc` only (see below)
- `clusters[].cluster.insecure-skip-tls-verify` (forwarded only when `true`; a cluster that
  omits it keeps kubex's normal system-trust-store/explicit-CA behavior)

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
- Namespace: `/var/run/secrets/kubernetes.io/serviceaccount/namespace`
- Server URL: from `KUBERNETES_SERVICE_HOST` and `KUBERNETES_SERVICE_PORT` environment variables

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
command via `anyio.run_process` and parses the `ExecCredential` JSON response) in an
`ExecRefreshableToken` and stores it on `ClientConfiguration.refreshable_token`. Both HTTP
backends call `ClientConfiguration.get_authorization_header()` on every request, which awaits
`ExecRefreshableToken.to_header()` — the exec command re-runs whenever the cached token is within
10 seconds of expiring.

Caveat: `ExecCredential.status.expirationTimestamp` is not read. The cached token is treated as
expiring after a fixed 60 seconds regardless of what the plugin actually reported, so a plugin
issuing longer- or shorter-lived tokens re-runs on that fixed cadence rather than the token's real
lifetime.

## OIDC

OIDC (`auth-provider: oidc`) is resolved the same way: `configure_from_kubeconfig()` wraps
`OIDCAuthProvider` in an `OidcRefreshableToken`. Only `auth-provider: oidc` is supported — any
other `auth-provider` name raises `ConfigurationError`. The same fixed-60-second refresh caveat
as the exec provider applies (the OIDC token response's real expiry is not read either).

If the identity provider rotates refresh tokens (e.g. Auth0, Okta, or Keycloak with rotation
enabled), a fresh refresh token issued during a kubex refresh is kept only in memory for the
life of the process — it is **not** written back to the kubeconfig file on disk. Combined with
the fixed 60-second refresh cadence above, this means the on-disk refresh token is invalidated
roughly once a minute; a fresh process (or a concurrent `kubectl` invocation reading the same
kubeconfig) will need to re-authenticate interactively once that has happened. Identity
providers that do not rotate refresh tokens for the client type in use (e.g. Google's OAuth
for installed applications) are unaffected.

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
```

The `namespace` parameter is populated by `configure_from_pod_env()` from the pod's service-account
namespace file. `Api`/`create_api()` fall back to it when a **namespace-scoped** resource is
created without an explicit `namespace=` argument — so running in-cluster and omitting the
namespace scopes `get()`/`create()`/`list()`/`watch()` to the pod's own namespace, rather than
"all namespaces". Pass `namespace=None` explicitly to opt back into all-namespaces behavior, or a
specific string to target a different namespace. Cluster-scoped resources never receive a
namespace, configured or not.
