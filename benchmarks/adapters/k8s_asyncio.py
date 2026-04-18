from __future__ import annotations

import time
from typing import Any, ClassVar

from .protocol import (
    CAP_LOGS,
    CAP_NAMESPACE_LIST,
    CAP_POD_CRUD,
    CAP_WATCH,
    PodSpecLite,
    StreamSample,
)


class K8sAsyncioAdapter:
    """Adapter over tomplus/kubernetes_asyncio.

    Uses aiohttp internally (provided by the library). Supports asyncio only —
    kubernetes_asyncio does not support trio because aiohttp does not support
    trio. The runner excludes it from trio measurement passes.
    """

    name: ClassVar[str] = "k8s-asyncio"
    capabilities: ClassVar[frozenset[str]] = frozenset(
        {CAP_POD_CRUD, CAP_NAMESPACE_LIST, CAP_WATCH, CAP_LOGS}
    )
    runtime: ClassVar[str] = "asyncio"

    def __init__(self) -> None:
        self._api_client: Any = None
        self._core: Any = None

    async def setup(self, kubeconfig_path: str) -> None:
        from kubernetes_asyncio import client, config  # type: ignore[import-not-found]

        await config.load_kube_config(config_file=kubeconfig_path)
        self._api_client = client.ApiClient()
        self._core = client.CoreV1Api(self._api_client)

    async def teardown(self) -> None:
        if self._api_client is not None:
            await self._api_client.close()
            self._api_client = None
            self._core = None

    async def list_pods(self, namespace: str) -> int:
        result = await self._core.list_namespaced_pod(namespace=namespace)
        return len(result.items)

    async def get_pod(self, namespace: str, name: str) -> None:
        await self._core.read_namespaced_pod(name=name, namespace=namespace)

    async def create_pod(self, namespace: str, spec: PodSpecLite) -> None:
        from kubernetes_asyncio.client.models import (  # type: ignore[import-not-found]
            V1Container,
            V1ObjectMeta,
            V1Pod,
            V1PodSpec,
        )

        body = V1Pod(
            api_version="v1",
            kind="Pod",
            metadata=V1ObjectMeta(name=spec.name, namespace=namespace),
            spec=V1PodSpec(
                containers=[
                    V1Container(
                        name="c",
                        image=spec.image,
                        command=list(spec.command) if spec.command else None,
                    )
                ]
            ),
        )
        await self._core.create_namespaced_pod(namespace=namespace, body=body)

    async def delete_pod(self, namespace: str, name: str) -> None:
        await self._core.delete_namespaced_pod(
            name=name, namespace=namespace, grace_period_seconds=0
        )

    async def list_namespaces(self) -> int:
        result = await self._core.list_namespace()
        return len(result.items)

    async def watch_pods(self, namespace: str, n_events: int) -> StreamSample:
        from kubernetes_asyncio.watch import Watch  # type: ignore[import-not-found]

        watcher = Watch()
        intervals: list[int] = []
        count = 0
        prev: int | None = None
        try:
            async for _event in watcher.stream(
                self._core.list_namespaced_pod, namespace=namespace
            ):
                now = time.perf_counter_ns()
                if prev is not None:
                    intervals.append(now - prev)
                prev = now
                count += 1
                if count >= n_events:
                    break
        finally:
            await watcher.close()
        return StreamSample(count=count, inter_arrival_ns=intervals)

    async def stream_logs(
        self, namespace: str, name: str, n_lines: int
    ) -> StreamSample:
        resp = await self._core.read_namespaced_pod_log(
            name=name,
            namespace=namespace,
            follow=True,
            _preload_content=False,
        )
        intervals: list[int] = []
        count = 0
        prev: int | None = None
        try:
            async for raw_line in resp.content:
                if not raw_line:
                    continue
                now = time.perf_counter_ns()
                if prev is not None:
                    intervals.append(now - prev)
                prev = now
                count += 1
                if count >= n_lines:
                    break
        finally:
            resp.release()
        return StreamSample(count=count, inter_arrival_ns=intervals)
