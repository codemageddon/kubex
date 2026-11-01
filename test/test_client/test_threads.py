"""Clients on separate threads, each running its own event loop."""

from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import anyio
import pytest
from aiohttp import web

import kubex.configuration.configuration as configuration_module
from kubex.api import Api
from kubex.client import ClientChoice, create_client
from kubex.configuration import ClientConfiguration
from kubex.k8s.v1_35.core.v1.pod import Pod

from ._servers import ThreadedAioServer

_COMBOS = (
    ("asyncio", ClientChoice.AIOHTTP),
    ("asyncio", ClientChoice.HTTPX),
    ("trio", ClientChoice.HTTPX),
)


def _pod(name: str) -> dict[str, Any]:
    return {
        "apiVersion": "v1",
        "kind": "Pod",
        "metadata": {"name": name, "namespace": "default"},
    }


def test_clients_on_separate_threads_share_one_configuration(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    token_file = tmp_path / "token"
    token_file.write_text("file-token")
    # Re-read the token file on every request, from every thread at once.
    monkeypatch.setattr(configuration_module, "TOKEN_REFRESH_INTERVAL", -1)
    wrong_auth: list[str | None] = []

    def check_auth(request: web.Request) -> None:
        auth = request.headers.get("Authorization")
        if auth != "Bearer file-token":
            wrong_auth.append(auth)

    async def list_pods(request: web.Request) -> web.Response:
        check_auth(request)
        items = [_pod(f"pod-{i}") for i in range(3)]
        return web.json_response(
            {"apiVersion": "v1", "kind": "PodList", "metadata": {}, "items": items}
        )

    async def get_pod(request: web.Request) -> web.Response:
        check_auth(request)
        return web.json_response(_pod(request.match_info["name"]))

    app = web.Application()
    app.router.add_get("/api/v1/namespaces/default/pods", list_pods)
    app.router.add_get("/api/v1/namespaces/default/pods/{name}", get_pod)
    threads = 2 * len(_COMBOS)
    barrier = threading.Barrier(threads)

    with ThreadedAioServer(app) as server:
        # The file's token takes precedence over the inline one, so every
        # request from every thread must carry it.
        config = ClientConfiguration(
            url=server.url,
            token="inline-token",
            token_file=token_file,
            try_refresh_token=True,
        )

        def worker(idx: int) -> None:
            backend, choice = _COMBOS[idx % len(_COMBOS)]

            async def main() -> None:
                async with await create_client(config, choice) as client:
                    api: Api[Pod] = Api(Pod, client=client, namespace="default")
                    for k in range(10):
                        listed = await api.list()
                        assert len(listed.items) == 3
                        pod = await api.get(f"pod-{k}")
                        assert pod.metadata is not None
                        assert pod.metadata.name == f"pod-{k}"

            barrier.wait()
            anyio.run(main, backend=backend)

        with ThreadPoolExecutor(threads) as pool:
            list(pool.map(worker, range(threads)))

    assert wrong_auth == []
