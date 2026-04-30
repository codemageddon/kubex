# Advanced

This section covers advanced topics for production use and deeper integration.

<div class="grid cards" markdown>

-   **Multi-version Kubernetes**

    ---

    Use separate model packages (`kubex-k8s-1-32` through `kubex-k8s-1-37`) to target specific cluster versions, or mix versions in a single application.

    [Multi-version K8s](multi-version-k8s.md)

-   **Clients & Runtimes**

    ---

    Choose between `aiohttp` (faster, asyncio-only) and `httpx` (asyncio + trio), and understand the WebSocket support matrix for `exec`, `attach`, and `portforward`.

    [Clients & Runtimes](clients-runtimes.md)

-   **Authentication**

    ---

    Configure kubeconfig-based, in-cluster, and exec-provider authentication. Learn how `create_client()` auto-detects the right method.

    [Authentication](authentication.md)

-   **Benchmarks**

    ---

    Performance comparison against `kubernetes-asyncio`: latency, memory, and allocations across list, watch, and streaming scenarios, with instructions to reproduce results.

    [Benchmarks](benchmarks.md)

</div>
