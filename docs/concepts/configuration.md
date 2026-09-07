# Configuration

Kubex builds cluster credentials from `ClientConfiguration`. You can construct it manually or let the library auto-load it from your environment.

## Auto-loading

`create_client()` (and `create_api()`) call `_try_read_configuration()` when no configuration is provided. The lookup order is:

1. **kubeconfig file** — `configure_from_kubeconfig()` reads `~/.kube/config` (or the file pointed to by `$KUBECONFIG`).
2. **In-cluster environment** — `configure_from_pod_env()` reads the service-account token and CA bundle mounted inside a Pod (`/var/run/secrets/kubernetes.io/serviceaccount/`).

If the kubeconfig file is not found, the library falls back to in-cluster automatically. Other kubeconfig errors (malformed file, missing context, permission denied, etc.) are propagated to the caller.

## `ClientConfiguration`

!!! note "Operational options live elsewhere"
    Timeouts and API-warning logging are client-level concerns, not kubeconfig data. They belong on [`ClientOptions`](clients.md#clientoptions), not here.

`ClientConfiguration` holds all connection parameters:

```python
from kubex.configuration import ClientConfiguration

config = ClientConfiguration(
    url="https://my-cluster:6443",
    token="my-bearer-token",  # or token_file="/path/to/token"
    server_ca_file="/path/to/ca.crt",  # or insecure_skip_tls_verify=True
    namespace="default",
)
```

Key parameters:

| Parameter | Type | Description |
|---|---|---|
| `url` | `str` | Kubernetes API server URL |
| `token` | `str` | Static bearer token |
| `token_file` | `Path | str` | Path to a file containing the bearer token |
| `server_ca_file` | `Path | str` | CA certificate for TLS verification |
| `insecure_skip_tls_verify` | `bool` | Disable TLS verification (not for production) |
| `client_cert_file` / `client_key_file` | `Path | str` | Mutual TLS client certificate + key |
| `namespace` | `str \| None` | Populated by `configure_from_pod_env` from the pod's own namespace. `Api`/`create_api()` fall back to it for namespace-scoped resources created without an explicit `namespace=`; `None` (the default here) leaves their own "all namespaces" default in effect |
| `try_refresh_token` | `bool` | Re-read `token_file` every 60 s (for projected service-account tokens) |
| `refreshable_token` | `SupportsAuthorizationHeader` | An exec/OIDC token source (`ExecRefreshableToken` / `OidcRefreshableToken`); set automatically by `configure_from_kubeconfig()`, takes priority over `token`/`token_file` when present |

## `configure_from_kubeconfig()`

Reads a kubeconfig file and returns a `ClientConfiguration`. Resolves the current context and supports the following auth mechanisms:

- Bearer token (inline or from file)
- Client certificate + key (inline data or file paths)
- Exec credential provider (e.g., `aws eks get-token`, `gke-gcloud-auth-plugin`)
- OIDC (`auth-provider: oidc` only)

A context whose `auth-provider` is set to anything other than `oidc`, or whose `oidc` config
fails to validate, raises `ConfigurationError` instead of silently returning an unauthenticated
client. See [Exec credential provider](#exec-credential-provider) below.

```python
from kubex.configuration.file_config import configure_from_kubeconfig

config = await configure_from_kubeconfig()
```

To load a specific file (there is no `path=` parameter — read and parse it yourself, then pass
the resulting `KubeConfig`):

```python
from kubex.configuration.configuration import KubeConfig
from kubex.configuration.file_config import configure_from_kubeconfig
from pathlib import Path
from yaml import safe_load

raw = safe_load(Path("/home/user/.kube/my-config").read_text())
kube_config = KubeConfig.model_validate(raw)
config = await configure_from_kubeconfig(config=kube_config)
```

## `configure_from_pod_env()`

Reads in-cluster credentials from the standard Kubernetes service-account mount:

```python
from kubex.configuration.incluster_config import configure_from_pod_env

config = await configure_from_pod_env()
```

This is used automatically when your code runs inside a Pod and kubeconfig is not available.

## Exec credential provider

When a kubeconfig context uses an `exec:` credential plugin (common with AWS EKS, GKE, and other
managed clusters), `configure_from_kubeconfig()` resolves it by wrapping `ExecAuthProvider` in an
`ExecRefreshableToken` and storing it as `ClientConfiguration.refreshable_token`. The exec command
re-runs whenever the cached token is close to expiring; see [Authentication](../advanced/authentication.md#exec-provider)
for the refresh-timing caveat.

For full details on the exec provider and OIDC authentication, see [Authentication](../advanced/authentication.md).
