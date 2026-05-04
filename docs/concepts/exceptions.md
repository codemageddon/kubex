# Exceptions

All Kubex exceptions inherit from `KubexException`. The hierarchy mirrors the HTTP status codes returned by the Kubernetes API server.

## Exception hierarchy

```
KubexException
├── ConfgiurationError          # bad/missing config (note: intentional typo in class name)
└── KubexClientException        # any client-side problem
    └── KubexApiError[C]        # non-2xx HTTP response from the API server
        ├── BadRequest          # 400
        ├── Unauthorized        # 401
        ├── Forbidden           # 403
        ├── NotFound            # 404
        ├── MethodNotAllowed    # 405
        ├── Conflict            # 409
        ├── Gone                # 410
        ├── UnprocessableEntity # 422
        └── KubernetesError     # 500
```

## `KubexApiError`

`KubexApiError` is generic over the response body type (`str | Status`). When the API server returns a JSON `Status` object, `error.content` is a parsed `Status` instance. For plain-text error responses, it is a `str`.

```python
from kubex.core.exceptions import NotFound, KubexApiError

try:
    pod = await api.get("missing-pod")
except NotFound as e:
    print(e.status)   # HTTPStatus.NOT_FOUND
    print(e.content)  # Status object or str with the error message
```

Every `KubexApiError` subclass has a `status` class attribute (an `HTTPStatus` value) that matches the HTTP status code it represents.

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

## `ConfgiurationError`

Raised when the client cannot be configured — for example, when `httpx-ws` is not installed and you attempt to use `api.exec`, or when required configuration fields are missing. Note: the class name has an intentional typo preserved from the original codebase.

```python
from kubex.core.exceptions import ConfgiurationError

try:
    async with api.exec.stream("my-pod", command=["sh"]) as session:
        ...
except ConfgiurationError as e:
    print("missing dependency or bad config:", e)
```
