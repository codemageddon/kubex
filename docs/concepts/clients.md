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
