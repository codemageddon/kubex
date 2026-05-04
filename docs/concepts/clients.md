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

Pass `options=` to control how the client behaves at request time (timeouts, proxy, pool size, etc.). See [ClientOptions](#clientoptions) below for details:

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

### `proxy`

Configures an outbound HTTP proxy for all requests. Accepted values:

| Value | Meaning |
|---|---|
| `None` (the default) | No proxy |
| `str` | Single proxy URL for all requests, e.g. `"http://proxy.corp.example.com:8080"` |
| `dict[str, str]` | Per-scheme map with `"http"` and/or `"https"` keys |

```python
# Single proxy URL (basic auth via userinfo)
options = ClientOptions(proxy="http://user:pass@proxy.corp.example.com:8080")

# Per-scheme map
options = ClientOptions(proxy={"https": "http://proxy.corp.example.com:8080"})
```

### `keep_alive`

Whether to reuse idle connections (connection keep-alive). Set to `False` to close each connection immediately after use.

```python
# Disable keep-alive
options = ClientOptions(keep_alive=False)
```

### `keep_alive_timeout`

Idle-connection lifetime in seconds. Uses the three-state sentinel pattern:

| Value | Meaning |
|---|---|
| `...` (the default) | Library default (httpx: 5 s; aiohttp: 15 s) |
| `None` | Keep idle connections indefinitely (httpx only; aiohttp warns) |
| `float >= 0` | Explicit lifetime in seconds |

```python
# Keep idle connections for 60 seconds
options = ClientOptions(keep_alive_timeout=60.0)

# Indefinite (httpx only)
options = ClientOptions(keep_alive_timeout=None)
```

### `buffer_size`

HTTP-response read buffer size in bytes. Uses the three-state sentinel pattern:

| Value | Meaning |
|---|---|
| `...` (the default) | Kubex default of `2**21` bytes (preserves current aiohttp behavior) |
| `None` | Library default (aiohttp: `2**16` bytes) |
| `int > 0` | Explicit buffer size in bytes |

```python
# Use a 1 MiB read buffer
options = ClientOptions(buffer_size=1024 * 1024)

# Use aiohttp's own default
options = ClientOptions(buffer_size=None)
```

!!! note "httpx asymmetry"
    httpx has no equivalent buffer-size knob. Setting `buffer_size` to anything other
    than `...` on an httpx-backed client emits a `UserWarning` and is otherwise ignored.

### `ws_max_message_size`

Maximum WebSocket frame size in bytes for `exec`, `attach`, and `portforward`. Uses the three-state sentinel pattern:

| Value | Meaning |
|---|---|
| `...` (the default) | Kubex default of `2**21` bytes (preserves current behavior on both backends) |
| `None` | No cap (passes `0` on the wire) |
| `int > 0` | Explicit cap in bytes |

```python
# Allow frames up to 8 MiB (for large exec output)
options = ClientOptions(ws_max_message_size=8 * 1024 * 1024)

# No cap
options = ClientOptions(ws_max_message_size=None)
```

### `pool_size`

Total connection pool size (all hosts combined). Uses the three-state sentinel pattern:

| Value | Meaning |
|---|---|
| `...` (the default) | Library default (both backends: 100) |
| `None` | Unlimited |
| `int > 0` | Explicit connection limit |

```python
# Reduce pool to 10 connections total
options = ClientOptions(pool_size=10)

# Unlimited
options = ClientOptions(pool_size=None)
```

### `pool_size_per_host`

Per-host connection pool size. Uses the three-state sentinel pattern:

| Value | Meaning |
|---|---|
| `...` (the default) | Library default (aiohttp: 0, meaning no per-host limit) |
| `None` | Unlimited |
| `int > 0` | Explicit per-host limit |

```python
# Limit to 5 connections per host
options = ClientOptions(pool_size_per_host=5)
```

!!! note "httpx asymmetry"
    httpx has no per-host pool limit. Setting `pool_size_per_host` to anything other
    than `...` on an httpx-backed client emits a `UserWarning` and is otherwise ignored.

## Backend asymmetries

Some `ClientOptions` fields behave differently (or are unsupported) depending on which HTTP backend is in use. A `UserWarning` is emitted on first use when a field has no effect.

| Field | httpx | aiohttp |
|---|---|---|
| `proxy=str` | `proxy=str` on `AsyncClient` | `proxy=str` on `ClientSession` |
| `proxy=dict` | All entries applied via `mounts=` | Only the entry matching the API server's URL scheme is used; other entries are dropped with a warning |
| `keep_alive=False` | `Limits(max_keepalive_connections=0)` | `TCPConnector(force_close=True)` |
| `keep_alive_timeout` | `Limits(keepalive_expiry=float\|None)` | `TCPConnector(keepalive_timeout=float)` — `None` is unsupported; warning emitted |
| `buffer_size` | **Ignored** — warning emitted | `ClientSession(read_bufsize=int)` |
| `ws_max_message_size` | `aconnect_ws(max_message_size_bytes=int)` | `ws_connect(max_msg_size=int)` |
| `pool_size` | `Limits(max_connections=int\|None)` | `TCPConnector(limit=int)` — `None` maps to `0` (unlimited) |
| `pool_size_per_host` | **Ignored** — warning emitted | `TCPConnector(limit_per_host=int)` — `None` maps to `0` (unlimited) |

Cross-reference: see [Timeouts](../operations/timeouts.md) for the note on `Timeout.write` and `Timeout.pool` being httpx-only fields.

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
