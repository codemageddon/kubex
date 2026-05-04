"""Demonstrates every ClientOptions knob.

Run against a real cluster (or any reachable API server) to see the effects.
Most settings here are intentionally set to non-default values for illustration;
in production you would only set the ones you need.
"""

import asyncio

from kubex.api import Api
from kubex.client import ClientOptions, create_client
from kubex.core.params import Timeout
from kubex.k8s.v1_35.core.v1.namespace import Namespace


async def main() -> None:
    # All new fields shown with representative values.
    # Replace proxy URL and pool sizes to match your environment.
    options = ClientOptions(
        # HTTP timeouts — 30 s total, 5 s connect
        timeout=Timeout(total=30.0, connect=5.0),
        # Silence deprecated-API warnings from the server
        log_api_warnings=False,
        # Route all traffic through a corporate HTTPS proxy.
        # Use a dict to apply different proxies per scheme:
        #   proxy={"http": "http://...", "https": "http://..."}
        proxy="http://proxy.corp.example.com:8080",
        # Keep idle connections alive
        keep_alive=True,
        # Close idle connections after 60 s (library default: httpx=5 s, aiohttp=15 s)
        keep_alive_timeout=60.0,
        # HTTP-response read buffer: 4 MiB
        # (ignored on httpx — UserWarning emitted; aiohttp default is 2**21)
        buffer_size=4 * 1024 * 1024,
        # Max WebSocket frame for exec/attach/portforward: 8 MiB
        # Pass None for no cap; default is 2**21 on both backends.
        ws_max_message_size=8 * 1024 * 1024,
        # Total connection pool: 50 connections across all hosts
        # Pass None for unlimited; library default is 100.
        pool_size=50,
        # Per-host connection limit: 10
        # (ignored on httpx — UserWarning emitted; aiohttp default is 0 = no limit)
        pool_size_per_host=10,
    )

    async with await create_client(options=options) as client:
        api: Api[Namespace] = Api(Namespace, client=client)
        namespaces = await api.list()
        for ns in namespaces.items:
            print(ns.metadata.name if ns.metadata else "<unknown>")


if __name__ == "__main__":
    asyncio.run(main())
