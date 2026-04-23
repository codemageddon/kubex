from __future__ import annotations

import importlib
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.codegen import model_emitter, resource_detector, spec_loader
from scripts.codegen.package_builder import RenderInputs, write_package

FIXTURE = Path(__file__).parent / "fixtures" / "mini_swagger.json"


@pytest.fixture
def generated_package(tmp_path: Path) -> Path:
    """Run the generator against mini_swagger.json into `tmp_path` and return the package root."""
    spec = spec_loader.load_swagger(FIXTURE)
    resources = resource_detector.detect_resources(spec.definitions, spec.paths)
    build = model_emitter.build_modules(
        k8s_version_tag="v1_30",
        definitions=spec.definitions,
        resources=resources,
    )
    pkg = write_package(
        RenderInputs(
            output_root=tmp_path,
            k8s_version="1.30",
            k8s_version_tag="v1_30",
            package_version="0.0.0.dev0",
            modules=build.modules,
            shared_enums=build.shared_enums,
        )
    )
    return pkg


def test_package_layout(generated_package: Path) -> None:
    src = generated_package / "kubex" / "k8s" / "v1_30"
    assert (src / "__init__.py").is_file()
    assert (src / "_common.py").is_file()
    # Nested group/version directories
    assert (src / "core" / "v1" / "__init__.py").is_file()
    assert (src / "core" / "v1" / "node.py").is_file()
    assert (src / "core" / "v1" / "node_list.py").is_file()
    assert (src / "core" / "v1" / "node_address.py").is_file()
    assert (src / "core" / "v1" / "node_status.py").is_file()
    assert (src / "apps" / "v1" / "__init__.py").is_file()
    assert (src / "apps" / "v1" / "deployment.py").is_file()
    assert (src / "apps" / "v1" / "deployment_list.py").is_file()
    assert (generated_package / "pyproject.toml").is_file()
    # Old flat files should NOT exist
    assert not (src / "core_v1.py").exists()
    assert not (src / "apps_v1.py").exists()


def test_generated_is_ruff_clean(generated_package: Path) -> None:
    result = subprocess.run(
        ["uv", "run", "ruff", "check", str(generated_package)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    fmt = subprocess.run(
        ["uv", "run", "ruff", "format", "--check", str(generated_package)],
        capture_output=True,
        text=True,
    )
    assert fmt.returncode == 0, fmt.stdout + fmt.stderr


def test_generated_imports_and_validates(generated_package: Path) -> None:
    """Import the generated modules and exercise them against sample JSON.

    `kubex` is a PEP 420 namespace package.  Adding the generated package
    root to `sys.path` lets the import system discover `kubex.k8s.*`
    alongside the main `kubex.*` sub-packages.
    """
    extra_path = str(generated_package)
    sys.path.insert(0, extra_path)
    try:
        for mod in list(sys.modules):
            if mod.startswith("kubex.k8s.v1_30"):
                sys.modules.pop(mod, None)
        # Re-import kubex so the namespace path is recalculated.
        if "kubex" in sys.modules:
            importlib.invalidate_caches()
            importlib.reload(sys.modules["kubex"])

        node_mod = importlib.import_module("kubex.k8s.v1_30.core.v1.node")
        node_list_mod = importlib.import_module("kubex.k8s.v1_30.core.v1.node_list")
        deployment_mod = importlib.import_module("kubex.k8s.v1_30.apps.v1.deployment")
        deployment_list_mod = importlib.import_module(
            "kubex.k8s.v1_30.apps.v1.deployment_list"
        )

        Node = node_mod.Node
        NodeList = node_list_mod.NodeList
        Deployment = deployment_mod.Deployment
        DeploymentList = deployment_list_mod.DeploymentList

        assert Node.__RESOURCE_CONFIG__.url() == "/api/v1/nodes"
        assert Node.__RESOURCE_CONFIG__.url(name="nd1") == "/api/v1/nodes/nd1"
        assert (
            Deployment.__RESOURCE_CONFIG__.url(namespace="ns1")
            == "/apis/apps/v1/namespaces/ns1/deployments"
        )

        assert Node.__RESOURCE_CONFIG__.list_model is NodeList
        assert Deployment.__RESOURCE_CONFIG__.list_model is DeploymentList

        node = Node.model_validate(
            {
                "apiVersion": "v1",
                "kind": "Node",
                "metadata": {"name": "worker-1"},
                "status": {
                    "addresses": [
                        {
                            "type": "InternalIP",
                            "address": "10.0.0.1",
                            "internalIP": "10.0.0.1",
                            "podIPs": ["10.0.0.1"],
                            "someNiceAPI": "api-1",
                        }
                    ],
                    "phase": "Running",
                },
            }
        )
        assert node.metadata.name == "worker-1"
        assert node.status is not None
        addr = node.status.addresses[0]
        assert addr.internal_ip == "10.0.0.1"
        assert addr.pod_ips == ["10.0.0.1"]
        assert addr.some_nice_api == "api-1"
        assert node.status.phase.value == "Running"
        dumped = node.model_dump(by_alias=True, exclude_none=True)
        assert dumped["status"]["addresses"][0]["internalIP"] == "10.0.0.1"
        assert dumped["status"]["addresses"][0]["podIPs"] == ["10.0.0.1"]
        assert dumped["status"]["phase"] == "Running"

        with pytest.raises(ValueError):
            Node.__RESOURCE_CONFIG__.url(namespace="x")

        from kubex_core.models.interfaces import (
            HasScaleSubresource,
            HasStatusSubresource,
        )

        assert issubclass(Deployment, HasStatusSubresource)
        assert issubclass(Deployment, HasScaleSubresource)
    finally:
        sys.path.remove(extra_path)
        for mod in list(sys.modules):
            if mod.startswith("kubex.k8s.v1_30"):
                sys.modules.pop(mod, None)


def test_enum_placement_inline(generated_package: Path) -> None:
    """Single-use enums live inside the class file, not in _common.py."""
    src = generated_package / "kubex" / "k8s" / "v1_30"
    node_status = (src / "core" / "v1" / "node_status.py").read_text()
    deployment_condition = (src / "apps" / "v1" / "deployment_condition.py").read_text()
    common = (src / "_common.py").read_text()

    assert "class NodeStatusPhase(str, Enum):" in node_status
    assert "class DeploymentConditionType(str, Enum):" in deployment_condition
    assert "class NodeStatusPhase" not in common
    assert "class DeploymentConditionType" not in common


def test_common_exports_intorstring(generated_package: Path) -> None:
    common = (generated_package / "kubex" / "k8s" / "v1_30" / "_common.py").read_text()
    assert "IntOrString = int | str" in common


def test_init_has_all(generated_package: Path) -> None:
    init = (generated_package / "kubex" / "k8s" / "v1_30" / "__init__.py").read_text()
    assert "__all__" in init
    assert '"Node"' in init or "'Node'" in init
    assert '"Deployment"' in init or "'Deployment'" in init
    # No INDEX, no re-export imports
    assert "INDEX" not in init
    assert "from kubex" not in init


def test_new_marker_bases_emitted() -> None:
    """Verify model_emitter produces correct bases for resources with new subresource flags."""
    from typing import Any

    definitions: dict[str, Any] = {
        "io.k8s.api.core.v1.Pod": {
            "type": "object",
            "properties": {
                "apiVersion": {"type": "string"},
                "kind": {"type": "string"},
            },
            "x-kubernetes-group-version-kind": [
                {"group": "", "kind": "Pod", "version": "v1"}
            ],
        },
    }
    pod_gvk = {
        "x-kubernetes-group-version-kind": {
            "group": "",
            "kind": "Pod",
            "version": "v1",
        }
    }
    eviction_gvk = {
        "x-kubernetes-group-version-kind": {
            "group": "policy",
            "kind": "Eviction",
            "version": "v1",
        }
    }
    paths: dict[str, Any] = {
        "/api/v1/namespaces/{namespace}/pods": {"get": pod_gvk},
        "/api/v1/namespaces/{namespace}/pods/{name}": {"get": pod_gvk},
        "/api/v1/namespaces/{namespace}/pods/{name}/status": {"put": pod_gvk},
        "/api/v1/namespaces/{namespace}/pods/{name}/log": {"get": pod_gvk},
        "/api/v1/namespaces/{namespace}/pods/{name}/eviction": {"post": eviction_gvk},
        "/api/v1/namespaces/{namespace}/pods/{name}/ephemeralcontainers": {
            "get": pod_gvk
        },
        "/api/v1/namespaces/{namespace}/pods/{name}/resize": {"get": pod_gvk},
        "/api/v1/namespaces/{namespace}/pods/{name}/attach": {"post": pod_gvk},
        "/api/v1/namespaces/{namespace}/pods/{name}/exec": {"post": pod_gvk},
        "/api/v1/namespaces/{namespace}/pods/{name}/portforward": {"post": pod_gvk},
    }
    resources = resource_detector.detect_resources(definitions, paths)
    build = model_emitter.build_modules(
        k8s_version_tag="v1_30",
        definitions=definitions,
        resources=resources,
    )
    pod_module = build.modules["kubex.k8s.v1_30.core.v1.pod"]
    pod_class = pod_module.classes[0]
    assert pod_class.class_name == "Pod"
    assert "NamespaceScopedEntity" in pod_class.bases
    assert "HasLogs" in pod_class.bases
    assert "Evictable" in pod_class.bases
    assert "HasStatusSubresource" in pod_class.bases
    assert "HasEphemeralContainers" in pod_class.bases
    assert "HasResize" in pod_class.bases
    assert "HasAttach" in pod_class.bases
    assert "HasExec" in pod_class.bases
    assert "HasPortForward" in pod_class.bases
