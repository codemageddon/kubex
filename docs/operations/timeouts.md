# Timeouts

Kubex separates two independent timeout concepts:

- **HTTP client timeout** (`request_timeout`) — how long to wait for the HTTP call to complete (connect + response).
- **Kubernetes server-side timeout** (`timeout_seconds`) — sent as the `timeoutSeconds` query parameter; the API server closes the stream or returns a result after this many seconds. Spelled `timeout_seconds` consistently across `list()`, `delete_collection()`, `watch()`, and `metadata.list()`.

## `Timeout` and `TimeoutTypes`

`Timeout` is the structured object for configuring HTTP-level timeouts:

```python
from kubex.core.params import Timeout

t = Timeout(total=30.0)  # 30 s total
t = Timeout(connect=5.0, read=60.0)  # separate connect / read
t = Timeout(total=30.0, connect=5.0, read=25.0)  # granular override
```

| Field | Description |
|---|---|
| `total` | Overall wall-clock timeout in seconds for the whole request, on both backends. Also the default for unset granular fields. |
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

If no `options` is provided (or `timeout=...`, the default), the underlying HTTP library's own default applies (httpx: 5 s per phase — connect, read, write, pool — with no overall cap; aiohttp: 300 s total, 30 s sock_connect).

A client-level default applies in full to regular (non-streaming) requests. Streaming calls only inherit its connection-setup part — see [Watch and long-lived streams](#watch-and-long-lived-streams).

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
    The Kubernetes API server applies its own default `timeoutSeconds` (usually
    somewhere between 30 and 60 minutes) when the client does not provide one. A `watch()` call
    will *not* stream forever — your loop must reconnect when the server closes
    the stream. Pass an explicit `timeout_seconds=` to make the bound visible
    in code, and combine with the [resume-after-`Gone` pattern](watch.md#resuming-after-gone)
    to keep the watch alive across reconnects.

A watch or a followed log stream legitimately goes quiet for long periods, so when `request_timeout` is **not** passed, `api.watch()`, `api.metadata.watch()` and `api.logs.stream()` use a *connect-only* timeout: the connection-setup bounds of the client default are kept (`connect`/`pool`, or `total` while connecting — the library defaults if `ClientOptions.timeout` is not set), and the `read` and `total` bounds are dropped. A stream therefore never fails just because no event arrived for a while.

An explicit `request_timeout` is applied to the stream as given — a short value will terminate the stream. (On streams, httpx applies a `total` per phase — e.g. as the longest allowed gap between chunks — rather than as a wall-clock limit; aiohttp applies it to the whole stream.)

```python
# Connect-only (the default): runs until the server closes the stream
async for event in api.watch(timeout_seconds=300):
    ...

# No HTTP timeout at all, not even for connecting
async for event in api.watch(request_timeout=None, timeout_seconds=300):
    ...
```

!!! tip "Detecting a dead connection"
    Without a read timeout, a connection that dies silently (e.g. a dropped NAT
    entry, no TCP reset) keeps the stream waiting. To bound that, pass
    `timeout_seconds` *and* a slightly larger client-side `request_timeout`:
    the server ends a healthy stream after `timeout_seconds`, so hitting the
    client timeout means the connection is gone.

    ```python
    async for event in api.watch(timeout_seconds=300, request_timeout=330):
        ...
    ```

    For log follows (which have no server-side timeout), use a generous `read`
    timeout instead, e.g. `request_timeout=Timeout(connect=10, read=600)`.

!!! warning "Two timeout parameters on `watch()`"
    `watch(timeout_seconds=N)` tells the *API server* to close the stream after N seconds.
    `watch(request_timeout=M)` tells the *HTTP client* to abort the connection after M seconds.
    They are independent — set both if you want server-side control *and* a client-side safety net.

## When a timeout fires

A client-side timeout raises `KubexTimeoutError` on both backends — for regular requests, streams (including mid-stream) and WebSocket handshakes. It subclasses both `KubexClientException` and the built-in `TimeoutError`, so either `except` clause catches it:

```python
from kubex.core.exceptions import KubexTimeoutError

try:
    pod = await api.get("my-pod", request_timeout=5)
except KubexTimeoutError:
    ...
```

Cancelling the calling task (e.g. an enclosing `anyio.move_on_after()`) is never converted: it propagates as the runtime's own cancellation.

## `timeout_seconds` on `list()` and `delete_collection()`

The `timeout_seconds` parameter on `list()` and `delete_collection()` is the Kubernetes server-side `timeoutSeconds` parameter, not the HTTP client timeout. It limits how long the API server will process the request:

```python
# Server-side: abort the list after 10 s (Kubernetes timeoutSeconds)
pods = await api.list(timeout_seconds=10)

# Client-side: abort the HTTP call after 15 s (HTTP read timeout)
pods = await api.list(request_timeout=15)
```
