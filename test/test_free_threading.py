"""Checks that only mean something on a free-threaded (no-GIL) build."""

from __future__ import annotations

import os
import subprocess
import sys
import sysconfig

import pytest

pytestmark = pytest.mark.skipif(
    not sysconfig.get_config_var("Py_GIL_DISABLED"),
    reason="needs a free-threaded build",
)

# kubex's entry points import every compiled dependency; httpx-ws and trio are
# only imported once used, so they are listed too.
_MODULES = (
    "kubex.api",
    "kubex.client.aiohttp",
    "kubex.client.httpx",
    "kubex.configuration",
    "kubex.k8s.v1_35.core.v1.pod",
    "httpx_ws",
    "trio",
)

_SCRIPT = """
import importlib, sys
for name in sys.argv[1:]:
    importlib.import_module(name)
    if sys._is_gil_enabled():
        sys.exit(f"importing {name} turned the GIL back on")
"""


def test_importing_kubex_keeps_the_gil_disabled() -> None:
    # CPython turns the GIL back on, with only a warning, when it loads an
    # extension module that does not declare free-threading support. Checked
    # in a fresh interpreter: this one has already imported pytest's plugins.
    env = {k: v for k, v in os.environ.items() if k != "PYTHON_GIL"}
    result = subprocess.run(
        [sys.executable, "-c", _SCRIPT, *_MODULES],
        capture_output=True,
        text=True,
        env=env,
        timeout=120,
    )
    assert result.returncode == 0, result.stderr
