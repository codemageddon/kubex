from __future__ import annotations

from collections.abc import AsyncGenerator, AsyncIterable
from contextlib import asynccontextmanager
from typing import TypeVar

T = TypeVar("T")


@asynccontextmanager
async def closing(stream: AsyncIterable[T]) -> AsyncGenerator[AsyncIterable[T], None]:
    """Closes `stream` on exit, when it can be closed.

    Every adapter owns the stream it reads, as in kube-runtime: when it stops,
    it closes that stream, so an abandoned chain does not keep a watch open (or a
    reflector subscription registered) until garbage collection.
    """
    try:
        yield stream
    finally:
        aclose = getattr(stream, "aclose", None)
        if aclose is not None:
            await aclose()
