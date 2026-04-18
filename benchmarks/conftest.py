"""Pytest fixtures for the benchmark suite.

Used by ``benchmarks/test_bench.py``. Provides a session-scoped K3s
testcontainer + seeded namespace; per-test adapter construction lives in
``test_bench.py`` because it also owns a private event loop.

Mirrors the pattern in ``test/e2e/conftest.py`` but lives independently so
the benchmarks package has no dependency on the e2e test tree.
"""

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path
from typing import Iterator

import pytest

from ._cluster import DEFAULT_K3S_IMAGE, seed_namespace, teardown_namespace


@pytest.fixture(scope="session")
def k3s_kubeconfig() -> Iterator[str]:
    """Session-scoped K3s cluster pinned to 1.33; yields kubeconfig path."""
    from testcontainers.k3s import K3SContainer  # type: ignore[import-untyped]

    container = K3SContainer(image=DEFAULT_K3S_IMAGE, enable_cgroup_mount=False)
    container.start()
    try:
        kube_path = Path(
            tempfile.mkstemp(prefix="bench-kubeconfig-", suffix=".yaml")[1]
        )
        kube_path.write_text(container.config_yaml())
        try:
            yield str(kube_path)
        finally:
            kube_path.unlink(missing_ok=True)
    finally:
        container.stop()


@pytest.fixture(scope="session")
def seeded_namespace(k3s_kubeconfig: str) -> Iterator[str]:
    """Namespace pre-populated with 500 pause pods + 1 log emitter."""
    ns = asyncio.run(seed_namespace(k3s_kubeconfig, n_pods=500))
    try:
        yield ns
    finally:
        asyncio.run(teardown_namespace(k3s_kubeconfig, ns))
