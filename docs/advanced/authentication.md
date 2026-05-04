# Authentication

Kubex supports three authentication methods: kubeconfig files, in-cluster service account tokens, and exec-provider credentials. Configuration is represented by `ClientConfiguration` and loaded by one of two async factory functions.

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
- OIDC (see below)

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

Exec provider authentication runs an external command to obtain a bearer token. This is the standard mechanism for cloud-provider CLI tools (AWS, GCP, Azure) and other external credential sources.

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

Kubex reads this via `configure_from_kubeconfig()`. The `ExecAuthProvider` class runs the command using `anyio.run_process`, parses the `ExecCredential` JSON response, and extracts the token. The token is then used as a bearer token in subsequent requests.

`ExecCredential.status.expirationTimestamp` is noted but token refresh on expiry is not yet fully implemented — the token is refreshed on the next call after the current one fails with `Unauthorized` (the auto-retry logic is planned). For long-running processes, re-configure periodically if needed.

## OIDC

OIDC (`auth-provider: oidc`) is parsed from the kubeconfig `auth-provider` block but token refresh is not yet implemented. OIDC support is listed as a planned feature in the roadmap. For current OIDC clusters, the exec provider (via `kubelogin` or similar) is the recommended workaround.

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

The `namespace` parameter sets the default namespace for all `Api` instances created from this client. It defaults to `"default"` if not specified.
