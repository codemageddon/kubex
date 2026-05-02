# Clients

Kubex separates the API layer (`Api[T]`) from the HTTP transport layer. You can swap transports without changing any application code.

## `create_client()`

The `create_client()` factory is the recommended way to get a client. It auto-detects which HTTP library is installed and returns an async context manager — `async with` ensures the underlying connection pool is closed cleanly:

```python
from kubex.client import create_client

async with await create_client() as client:
    # use the client
    ...
```

Auto-detection order: **aiohttp** is tried first, then **httpx**. If neither is installed, `create_client()` raises `ImportError`.

To force a specific client:

```python
from kubex.client import create_client, ClientChoise

# Force aiohttp
client = await create_client(client_class=ClientChoise.AIOHTTP)

# Force httpx
client = await create_client(client_class=ClientChoise.HTTPX)
```

Pass a pre-built `ClientConfiguration` to skip the auto-loading of kubeconfig / in-cluster credentials:

```python
from kubex.configuration import ClientConfiguration

config = ClientConfiguration(url="https://my-cluster:6443", token="my-token")
client = await create_client(configuration=config)
```

Pass `options=` to control how the client behaves at request time (timeouts, API-warning logging). See [ClientOptions](#clientoptions) below for details:

```python
from kubex.client import ClientOptions, create_client
from kubex.core.params import Timeout

client = await create_client(
    configuration=config,
    options=ClientOptions(timeout=Timeout(total=30.0), log_api_warnings=False),
)
```

## ClientOptions

`ClientOptions` carries per-process choices about how the HTTP client behaves. These settings have nothing to do with kubeconfig or the in-cluster environment — connection parameters live on [`ClientConfiguration`](configuration.md).

```python
from kubex.client import ClientOptions
from kubex.core.params import Timeout

options = ClientOptions(
    timeout=Timeout(total=30.0),
    log_api_warnings=True,  # default
)
```

### `timeout`

Controls the default HTTP timeout applied to every request made by this client. Accepted values:

| Value | Meaning |
|---|---|
| `...` (the default) | Use the HTTP library's own default (httpx: 5 s total; aiohttp: 300 s total, 30 s sock_connect) |
| `None` | Disable timeouts entirely |
| `int` or `float` | Treat as a `total` timeout in seconds; coerced to `Timeout` automatically |
| `Timeout(...)` | Use as-is for fine-grained per-phase control |

Individual calls can override this via the `request_timeout=` parameter. See [Timeouts](../operations/timeouts.md) for the full picture.

### `log_api_warnings`

When `True` (the default), kubex emits a Python `UserWarning` for every `Warning:` HTTP response header returned by the API server. The Kubernetes API server uses these headers to flag deprecated API usage (e.g. calling a removed API version). Set to `False` to silence them.

## `AioHttpClient`

Requires: `pip install "kubex[aiohttp]"`

aiohttp has WebSocket support built in — no extra package needed for `exec`, `attach`, and `portforward`. Supports asyncio only.

## `HttpxClient`

Requires: `pip install "kubex[httpx]"`

WebSocket support requires the extra `httpx-ws` package:
`pip install "kubex[httpx-ws]"` (includes httpx).

The httpx client is the only client that supports **trio** (in addition to asyncio).

## Client selection trade-offs

| Feature | aiohttp | httpx |
|---|---|---|
| asyncio support | yes | yes |
| trio support | no | yes |
| WebSocket (exec/attach/portforward) | built-in | requires `httpx-ws` extra |
| Auto-detection priority | 1st | 2nd |

For detailed guidance on choosing a client and runtime, see [Clients & Runtimes](../advanced/clients-runtimes.md).
