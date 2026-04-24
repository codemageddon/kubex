from __future__ import annotations

import pytest

from test.stub_client import StubClient as StubClient


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"
