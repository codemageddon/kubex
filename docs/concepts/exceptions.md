# Exceptions

All Kubex exceptions inherit from `KubexException`. API errors mirror the HTTP status codes returned by the Kubernetes API server; transport failures have their own backend-independent types, so code never needs to catch httpx- or aiohttp-specific exceptions.

## Exception hierarchy

```
KubexException
├── ConfigurationError          # bad/missing config
│   └── ConfigurationValueError # also a built-in ValueError
└── KubexClientException        # any client-side problem
    ├── KubexConnectionError    # server unreachable, TLS failure, connection dropped mid-response
    ├── KubexTimeoutError       # client-side timeout (also a built-in TimeoutError)
    └── KubexApiError[C]        # non-2xx HTTP response from the API server
        ├── BadRequest          # 400
        ├── Unauthorized        # 401
        ├── Forbidden           # 403
        ├── NotFound            # 404
        ├── MethodNotAllowed    # 405
        ├── Conflict            # 409
        ├── Gone                # 410
        ├── UnprocessableEntity # 422
        ├── TooManyRequests     # 429
        └── KubernetesError     # 500
```

Other status codes raise a plain `KubexApiError` with the matching `status`.

## `KubexApiError`

`KubexApiError` is generic over the response body type (`str | Status`). When the API server returns a JSON `Status` object, `error.content` is a parsed `Status` instance. For plain-text error responses, it is a `str`.

```python
from kubex.core.exceptions import NotFound, KubexApiError

try:
    pod = await api.get("missing-pod")
except NotFound as e:
    print(e.status)  # HTTPStatus.NOT_FOUND
    print(e.content)  # Status object or str with the error message
```

Every `KubexApiError` subclass has a `status` class attribute (an `HTTPStatus` value) that matches the HTTP status code it represents.

`str(error)` is a readable summary — the status code plus the `Status` message and reason, or the (truncated) plain-text body:

```python
except NotFound as e:
    print(e)  # 404 Not Found: pods "missing-pod" not found (reason: NotFound)
```

A rejected WebSocket upgrade (`exec`, `attach`, `portforward`) raises the same `KubexApiError` subclasses — e.g. `Forbidden` when the user may not create `pods/exec`, with the server's `Status` as `content`.

### `retry_after`

When the server sends a `Retry-After` header (or a `Status` with `details.retryAfterSeconds`) — typically with `429 Too Many Requests` (`TooManyRequests`) or `503 Service Unavailable` — the delay in seconds is available as `error.retry_after`; otherwise it is `None`.

```python
import anyio
from kubex.core.exceptions import TooManyRequests

try:
    await api.create(pod)
except TooManyRequests as e:
    await anyio.sleep(e.retry_after or 1)
```

## Handling errors

Catch the specific subclass you care about, or the base `KubexApiError` for any API error:

```python
from kubex.core.exceptions import (
    NotFound,
    Conflict,
    Forbidden,
    KubexApiError,
)

try:
    await api.create(pod)
except Conflict:
    print("resource already exists")
except Forbidden:
    print("insufficient permissions")
except KubexApiError as e:
    print(f"unexpected API error: {e.status} — {e.content}")
```

For a worked example see `examples/error_handling.py`.

## Connection errors and timeouts

`KubexConnectionError` is raised when the API server cannot be reached (connection refused, DNS or TLS failure, proxy error) or when the connection breaks while a response — including a watch or log stream — is being read. `KubexTimeoutError` is raised when a client-side timeout fires; it also subclasses the built-in `TimeoutError`. Both keep the underlying httpx/aiohttp exception as `__cause__`.

```python
from kubex.core.exceptions import KubexConnectionError, KubexTimeoutError

try:
    pods = await api.list()
except KubexTimeoutError:
    print("API server too slow")
except KubexConnectionError as e:
    print("API server unreachable:", e)
```

Task cancellation is never wrapped: it always propagates as the async runtime's own cancellation exception.

## `ConfigurationError`

Raised when the client cannot be configured — for example, when `httpx-ws` is not installed and you attempt to use `api.exec`, or when required configuration fields are missing.

`ConfigurationValueError` is the `ConfigurationError` raised when an exec credential plugin fails (non-zero exit, `interactiveMode: Always` without a terminal, no token in its output), an OIDC token response has no `id_token`, or the kubeconfig does not define the selected context or the cluster/user it names. It also subclasses the built-in `ValueError`, so `except ValueError` keeps working.

```python
from kubex.core.exceptions import ConfigurationError

try:
    async with api.exec.stream("my-pod", command=["sh"]) as session:
        ...
except ConfigurationError as e:
    print("missing dependency or bad config:", e)
```
