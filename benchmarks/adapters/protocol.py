from __future__ import annotations

from dataclasses import dataclass, field
from typing import ClassVar, Protocol, runtime_checkable


@dataclass(frozen=True, slots=True)
class PodSpecLite:
    name: str
    image: str = "registry.k8s.io/pause:3.9"
    command: tuple[str, ...] | None = None


@dataclass(frozen=True, slots=True)
class StreamSample:
    """Result of a streaming scenario (watch or logs)."""

    count: int
    inter_arrival_ns: list[int] = field(default_factory=list)


CAP_METADATA = "metadata"
CAP_WATCH = "watch"
CAP_LOGS = "logs"
CAP_NAMESPACE_LIST = "namespace_list"
CAP_POD_CRUD = "pod_crud"


@runtime_checkable
class ClientAdapter(Protocol):
    """Uniform async surface every library adapter must expose.

    Each scenario consumes only methods declared in this protocol so the
    same scenario module works across libraries and runtimes. Adapters that
    cannot serve a capability omit it from `capabilities` — the runner skips
    scenarios whose `required_capabilities` are not a subset.
    """

    name: ClassVar[str]
    capabilities: ClassVar[frozenset[str]]
    runtime: ClassVar[str]

    async def setup(self, kubeconfig_path: str) -> None: ...

    async def teardown(self) -> None: ...

    async def list_pods(self, namespace: str) -> int: ...

    async def get_pod(self, namespace: str, name: str) -> None: ...

    async def create_pod(self, namespace: str, spec: PodSpecLite) -> None: ...

    async def delete_pod(self, namespace: str, name: str) -> None: ...

    async def list_namespaces(self) -> int: ...

    async def watch_pods(self, namespace: str, n_events: int) -> StreamSample: ...

    async def stream_logs(
        self, namespace: str, name: str, n_lines: int
    ) -> StreamSample: ...
