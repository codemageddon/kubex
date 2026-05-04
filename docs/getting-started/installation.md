# Installation

Kubex requires **Python 3.10–3.14** and ships as a [PEP 561](https://peps.python.org/pep-0561/) typed package.

## Install

=== "uv"

    ```shell
    uv add kubex
    ```

=== "pip"

    ```shell
    pip install kubex
    ```

=== "poetry"

    ```shell
    poetry add kubex
    ```

=== "pdm"

    ```shell
    pdm add kubex
    ```

This installs the core library. To make actual requests to a Kubernetes cluster you need at least one HTTP client extra and one set of Kubernetes model packages.

## HTTP client extras

Kubex supports two HTTP client backends. Install the one you prefer:

| Extra | Installs | WebSocket (exec/attach/portforward) | trio support |
|---|---|---|---|
| `kubex[aiohttp]` | aiohttp | Yes (built-in) | No |
| `kubex[httpx]` | httpx | No — add `httpx-ws` | Yes |
| `kubex[httpx-ws]` | httpx + httpx-ws | Yes | Yes |

- `kubex[aiohttp]` is the default and the first one auto-detected by `create_client()`. WebSocket support is built in.
- Use `kubex[httpx]` for the trio backend without WebSocket subresources.
- Use `kubex[httpx-ws]` when you need `exec`, `attach`, or `portforward` with the httpx backend.

!!! note "Trio"
    Trio support is provided through the httpx backend only. `kubex[aiohttp]` works with asyncio only.

## Kubernetes model packages

Kubex ships separate model packages per Kubernetes minor version. Install the package matching your cluster:

| Extra | Kubernetes version |
|---|---|
| `kubex[k8s-1.32]` | 1.32 |
| `kubex[k8s-1.33]` | 1.33 |
| `kubex[k8s-1.34]` | 1.34 |
| `kubex[k8s-1.35]` | 1.35 |
| `kubex[k8s-1.36]` | 1.36 |
| `kubex[k8s-1.37]` | 1.37 |

You can install multiple versions simultaneously when managing clusters at different upgrade stages:

=== "uv"

    ```shell
    uv add "kubex[k8s-1.34,k8s-1.35]"
    ```

=== "pip"

    ```shell
    pip install "kubex[k8s-1.34,k8s-1.35]"
    ```

See [Multi-version Kubernetes](../advanced/multi-version-k8s.md) for details.

## Recommended combinations

For most users, pick one HTTP client and one K8s version:

=== "aiohttp"

    ```shell
    uv add "kubex[aiohttp,k8s-1.35]"
    # or: pip install "kubex[aiohttp,k8s-1.35]"
    ```

=== "httpx (no WebSocket)"

    ```shell
    uv add "kubex[httpx,k8s-1.35]"
    # or: pip install "kubex[httpx,k8s-1.35]"
    ```

=== "httpx with WebSocket"

    ```shell
    uv add "kubex[httpx-ws,k8s-1.35]"
    # or: pip install "kubex[httpx-ws,k8s-1.35]"
    ```

## Python version support

Kubex is tested and supported on Python 3.10 through 3.14.

## Next steps

Once installed, head to the [Quickstart](quickstart.md) to connect to your cluster and make your first request.
