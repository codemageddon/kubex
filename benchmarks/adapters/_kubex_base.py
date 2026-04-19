from __future__ import annotations

import time
from typing import ClassVar

from yaml import safe_load

from kubex.api.api import Api, create_api
from kubex.client.client import BaseClient
from kubex.configuration.configuration import KubeConfig
from kubex.configuration.file_config import configure_from_kubeconfig
from kubex.k8s.v1_35.core.v1.container import Container
from kubex.k8s.v1_35.core.v1.namespace import Namespace
from kubex.k8s.v1_35.core.v1.pod import Pod
from kubex.k8s.v1_35.core.v1.pod_spec import PodSpec
from kubex_core.models.metadata import ObjectMetadata

from .protocol import (
    CAP_LOGS,
    CAP_NAMESPACE_LIST,
    CAP_POD_CRUD,
    CAP_WATCH,
    PodSpecLite,
    StreamSample,
)


class KubexAdapterBase:
    """Shared implementation for all kubex adapters.

    Concrete subclasses pick the HTTP backend by overriding `_make_client` and
    declare the async runtime via the `runtime` class variable. Data-plane
    methods are identical across backends because kubex already abstracts
    them behind BaseClient.
    """

    name: ClassVar[str] = "kubex-base"
    capabilities: ClassVar[frozenset[str]] = frozenset(
        {CAP_POD_CRUD, CAP_NAMESPACE_LIST, CAP_WATCH, CAP_LOGS}
    )
    runtime: ClassVar[str] = "asyncio"

    def __init__(self) -> None:
        self._client: BaseClient | None = None
        self._pod_api: Api[Pod] | None = None
        self._namespace_api: Api[Namespace] | None = None

    async def _make_client(self, config_path: str) -> BaseClient:
        raise NotImplementedError

    async def setup(self, kubeconfig_path: str) -> None:
        with open(kubeconfig_path, "r") as fh:
            kube_config = KubeConfig.model_validate(safe_load(fh.read()))
        client_config = await configure_from_kubeconfig(kube_config)
        self._client = await self._build_client(client_config)
        await self._client.__aenter__()
        self._pod_api = await create_api(Pod, client=self._client)
        self._namespace_api = await create_api(Namespace, client=self._client)

    async def _build_client(self, config: object) -> BaseClient:
        raise NotImplementedError

    async def teardown(self) -> None:
        if self._client is not None:
            await self._client.__aexit__(None, None, None)
            self._client = None
            self._pod_api = None
            self._namespace_api = None

    def _pods(self) -> Api[Pod]:
        assert self._pod_api is not None, "setup() not called"
        return self._pod_api

    def _namespaces(self) -> Api[Namespace]:
        assert self._namespace_api is not None, "setup() not called"
        return self._namespace_api

    async def list_pods(self, namespace: str, *, limit: int | None = None) -> int:
        result = await self._pods().list(namespace=namespace, limit=limit)
        return len(result.items or [])

    async def get_pod(self, namespace: str, name: str) -> None:
        await self._pods().get(name, namespace=namespace)

    async def create_pod(self, namespace: str, spec: PodSpecLite) -> None:
        pod = Pod(
            metadata=ObjectMetadata(name=spec.name, namespace=namespace),
            spec=PodSpec(
                containers=[
                    Container(
                        name="c",
                        image=spec.image,
                        command=list(spec.command) if spec.command else None,
                    )
                ]
            ),
        )
        await self._pods().create(pod, namespace=namespace)

    async def delete_pod(self, namespace: str, name: str) -> None:
        await self._pods().delete(name, namespace=namespace, grace_period_seconds=0)

    async def list_namespaces(self) -> int:
        result = await self._namespaces().list()
        return len(result.items or [])

    async def watch_pods(self, namespace: str, n_events: int) -> StreamSample:
        assert self._pod_api is not None
        intervals: list[int] = []
        count = 0
        prev: int | None = None
        async for _event in self._pod_api.watch(
            namespace=namespace, allow_bookmarks=False
        ):
            now = time.perf_counter_ns()
            if prev is not None:
                intervals.append(now - prev)
            prev = now
            count += 1
            if count >= n_events:
                break
        return StreamSample(count=count, inter_arrival_ns=intervals)

    async def stream_logs(
        self, namespace: str, name: str, n_lines: int
    ) -> StreamSample:
        assert self._pod_api is not None
        intervals: list[int] = []
        count = 0
        prev: int | None = None
        async for _line in self._pod_api.stream_logs(name, namespace=namespace):
            now = time.perf_counter_ns()
            if prev is not None:
                intervals.append(now - prev)
            prev = now
            count += 1
            if count >= n_lines:
                break
        return StreamSample(count=count, inter_arrival_ns=intervals)
