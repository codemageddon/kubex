# Configuration

Kubex builds cluster credentials from `ClientConfiguration`. You can construct it manually or let the library auto-load it from your environment.

## Auto-loading

`create_client()` (and `create_api()`) call `_try_read_configuration()` when no configuration is provided. The lookup order is:

1. **kubeconfig file** — `configure_from_kubeconfig()` reads `~/.kube/config` (or the file pointed to by `$KUBECONFIG`).
2. **In-cluster environment** — `configure_from_pod_env()` reads the service-account token and CA bundle mounted inside a Pod (`/var/run/secrets/kubernetes.io/serviceaccount/`).

If kubeconfig parsing fails for any reason, the library falls back to in-cluster automatically and logs the error.

## `ClientConfiguration`

`ClientConfiguration` holds all connection parameters:

```python
from kubex.configuration import ClientConfiguration

config = ClientConfiguration(
    url="https://my-cluster:6443",
    token="my-bearer-token",          # or token_file="/path/to/token"
    server_ca_file="/path/to/ca.crt", # or insecure_skip_tls_verify=True
    namespace="default",
    timeout=30,                        # default HTTP timeout in seconds
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
| `namespace` | `str` | Default namespace (used by `configure_from_pod_env`) |
| `timeout` | `int | float | Timeout | None` | Default HTTP timeout; `None` = no timeout; `...` = library default |
| `try_refresh_token` | `bool` | Re-read `token_file` every 60 s (for projected service-account tokens) |

## `configure_from_kubeconfig()`

Reads a kubeconfig file and returns a `ClientConfiguration`. Resolves the current context and supports the following auth mechanisms:

- Bearer token (inline or from file)
- Client certificate + key (inline data or file paths)
- Exec credential provider (e.g., `aws eks get-token`, `gke-gcloud-auth-plugin`)

```python
from kubex.configuration.file_config import configure_from_kubeconfig

config = await configure_from_kubeconfig()
# or specify a path explicitly:
config = await configure_from_kubeconfig(path="/home/user/.kube/my-config")
```

## `configure_from_pod_env()`

Reads in-cluster credentials from the standard Kubernetes service-account mount:

```python
from kubex.configuration.incluster_config import configure_from_pod_env

config = await configure_from_pod_env()
```

This is used automatically when your code runs inside a Pod and kubeconfig is not available.

## Exec credential provider

When a kubeconfig context uses an `exec:` credential plugin (common with AWS EKS, GKE, and other managed clusters), `configure_from_kubeconfig()` resolves it by running the configured command and extracting the returned token. Token refresh is handled automatically on expiry.

For full details on the exec provider and OIDC authentication, see [Authentication](../advanced/authentication.md).
