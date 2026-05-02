# Timeouts

Kubex separates two independent timeout concepts:

- **HTTP client timeout** (`request_timeout`) — how long to wait for the HTTP call to complete (connect + response).
- **Kubernetes server-side timeout** (`timeout_seconds`) — sent as the `timeoutSeconds` query parameter; the API server closes the stream or returns a result after this many seconds. Spelled `timeout_seconds` consistently across `list()`, `delete_collection()`, `watch()`, and `metadata.list()`.

## `Timeout` and `TimeoutTypes`

`Timeout` is the structured object for configuring HTTP-level timeouts:

```python
from kubex.core.params import Timeout

t = Timeout(total=30.0)                          # 30 s total
t = Timeout(connect=5.0, read=60.0)              # separate connect / read
t = Timeout(total=30.0, connect=5.0, read=25.0)  # granular override
```

| Field | Description |
|---|---|
| `total` | Overall timeout in seconds. Acts as the default for unset granular fields. |
| `connect` | Timeout for establishing the TCP connection. |
| `read` | Timeout for reading the response body. |
| `write` | Timeout for writing the request body (httpx only). |
| `pool` | Timeout for acquiring a connection from the pool (httpx only). |

`TimeoutTypes = Timeout | float | int | None` — wherever a timeout is accepted, you can pass a number (treated as `total` seconds), a `Timeout` object, or `None` to disable timeouts entirely.

## Setting a client-level default

Pass `ClientOptions(timeout=…)` to `create_client()` to apply a default to every request made by that client:

```python
from kubex.client import ClientOptions, create_client
from kubex.core.params import Timeout

client = await create_client(
    options=ClientOptions(timeout=Timeout(total=30.0)),
)
```

If no `options` is provided (or `timeout=...`, the default), the underlying HTTP library's own default applies (httpx: 5 s total; aiohttp: 300 s total, 30 s sock_connect).

## Per-call override with `request_timeout`

Every `Api` method accepts `request_timeout=` to override the client default for that call alone. The parameter accepts `TimeoutTypes`:

```python
# Use the client default (Ellipsis = "inherit from client")
pod = await api.get("my-pod")

# Override to 5 seconds for this call
pod = await api.get("my-pod", request_timeout=5)

# Fine-grained override
pod = await api.get("my-pod", request_timeout=Timeout(connect=2.0, read=10.0))

# Disable timeouts for this call (long-running operation)
big_list = await api.list(request_timeout=None)
```

## The Ellipsis sentinel

| Value | Meaning |
|---|---|
| `...` (Ellipsis, the default) | Use the client-level timeout (or the HTTP library default if none was configured) |
| `None` | Disable timeouts for this call |
| `5` / `5.0` | 5 seconds total for this call |
| `Timeout(...)` | Structured per-field timeout for this call |

Passing `request_timeout=...` explicitly is the same as omitting it — both mean "use the client default."

## Watch and long-lived streams

!!! warning "Server-side default closes the stream"
    The Kubernetes API server applies its own default `timeoutSeconds` (typically
    around 5 minutes) when the client does not provide one. A `watch()` call
    will *not* stream forever — your loop must reconnect when the server closes
    the stream. Pass an explicit `timeout_seconds=` to make the bound visible
    in code, and combine with the [restart-on-`Gone` pattern](watch.md#restart-on-gone-pattern)
    to keep the watch alive across reconnects.

For `api.watch()` and log streaming, a short `read` timeout will terminate the stream prematurely. Either disable the HTTP timeout for these calls or set a generous `read` value:

```python
# No HTTP timeout on watch — the Kubernetes server-side timeout controls duration
async for event in api.watch(request_timeout=None, timeout_seconds=300):
    ...

# Or use a long read timeout
async for event in api.watch(request_timeout=Timeout(connect=5.0, read=600.0)):
    ...
```

!!! warning "Two timeout parameters on `watch()`"
    `watch(timeout_seconds=N)` tells the *API server* to close the stream after N seconds.
    `watch(request_timeout=M)` tells the *HTTP client* to abort the connection after M seconds.
    They are independent — set both if you want server-side control *and* a client-side safety net.

## `timeout_seconds` on `list()` and `delete_collection()`

The `timeout_seconds` parameter on `list()` and `delete_collection()` is the Kubernetes server-side `timeoutSeconds` parameter, not the HTTP client timeout. It limits how long the API server will process the request:

```python
# Server-side: abort the list after 10 s (Kubernetes timeoutSeconds)
pods = await api.list(timeout_seconds=10)

# Client-side: abort the HTTP call after 15 s (HTTP read timeout)
pods = await api.list(request_timeout=15)
```
