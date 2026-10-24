"""Local test servers that run on their own thread.

Running the server outside the test's event loop lets the same server back
tests on asyncio *and* trio (httpx), and keeps a slow/idle server from being
starved by the client under test.
"""

from __future__ import annotations

import asyncio
import shutil
import socket
import socketserver
import ssl
import subprocess
import threading
from pathlib import Path
from typing import Any, Callable

from aiohttp import web


class ThreadedAioServer:
    """Serve an aiohttp ``web.Application`` on 127.0.0.1 from a background thread."""

    def __init__(
        self, app: web.Application, ssl_context: ssl.SSLContext | None = None
    ) -> None:
        self.app = app
        self._ssl_context = ssl_context
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._runner: web.AppRunner | None = None
        self.port = 0

    @property
    def url(self) -> str:
        scheme = "https" if self._ssl_context is not None else "http"
        return f"{scheme}://127.0.0.1:{self.port}"

    def __enter__(self) -> ThreadedAioServer:
        ready = threading.Event()
        errors: list[BaseException] = []

        def _run() -> None:
            try:
                loop = asyncio.new_event_loop()
                self._loop = loop
                asyncio.set_event_loop(loop)
                runner = web.AppRunner(self.app, handle_signals=False)
                loop.run_until_complete(runner.setup())
                site = web.TCPSite(
                    runner, "127.0.0.1", 0, ssl_context=self._ssl_context
                )
                loop.run_until_complete(site.start())
                self._runner = runner
                server: Any = site._server
                self.port = server.sockets[0].getsockname()[1]
            except BaseException as exc:  # pragma: no cover - startup failure
                errors.append(exc)
                ready.set()
                return
            ready.set()
            loop.run_forever()

        self._thread = threading.Thread(target=_run, daemon=True)
        self._thread.start()
        ready.wait()
        if errors:
            raise errors[0]
        return self

    def __exit__(self, *exc_info: object) -> None:
        if self._loop is not None and self._runner is not None:
            runner = self._runner
            try:
                asyncio.run_coroutine_threadsafe(runner.cleanup(), self._loop).result(
                    timeout=5
                )
            except Exception:  # pragma: no cover - best-effort cleanup
                pass
            finally:
                self._loop.call_soon_threadsafe(self._loop.stop)
        if self._thread is not None:
            self._thread.join(timeout=5)


class RawHttpServer:
    """Accept TCP connections and hand each socket (after the request head) to ``handler``.

    For responses no well-behaved server framework would produce: truncated
    bodies, trickled bytes, abrupt disconnects.
    """

    def __init__(self, handler: Callable[[socket.socket], None]) -> None:
        outer_handler = handler

        class _Handler(socketserver.BaseRequestHandler):
            def handle(self) -> None:
                sock: socket.socket = self.request
                data = b""
                while b"\r\n\r\n" not in data:
                    chunk = sock.recv(65536)
                    if not chunk:
                        return
                    data += chunk
                try:
                    outer_handler(sock)
                except OSError:
                    pass

        class _Server(socketserver.ThreadingTCPServer):
            daemon_threads = True
            allow_reuse_address = True

        self._server = _Server(("127.0.0.1", 0), _Handler)
        self._thread: threading.Thread | None = None

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self._server.server_address[1]}"

    def __enter__(self) -> RawHttpServer:
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, *exc_info: object) -> None:
        self._server.shutdown()
        self._server.server_close()


def make_self_signed_cert(directory: Path, dns_name: str) -> tuple[Path, Path] | None:
    """Create a self-signed cert/key for ``dns_name`` with the ``openssl`` CLI.

    Returns ``None`` when ``openssl`` is unavailable or fails.
    """
    openssl = shutil.which("openssl")
    if openssl is None:
        return None
    cert = directory / "server.crt"
    key = directory / "server.key"
    result = subprocess.run(
        [
            openssl,
            "req",
            "-x509",
            "-newkey",
            "rsa:2048",
            "-nodes",
            "-sha256",
            "-days",
            "2",
            "-keyout",
            str(key),
            "-out",
            str(cert),
            "-subj",
            f"/CN={dns_name}",
            "-addext",
            f"subjectAltName=DNS:{dns_name}",
            "-addext",
            "basicConstraints=critical,CA:TRUE",
            "-addext",
            "keyUsage=critical,digitalSignature,keyEncipherment,keyCertSign",
            "-addext",
            "extendedKeyUsage=serverAuth",
        ],
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    return cert, key
