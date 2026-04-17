from __future__ import annotations

import importlib.util
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
    src = generated_package / "src" / "kubex" / "k8s" / "v1_30"
    assert (src / "__init__.py").is_file()
    assert (src / "_common.py").is_file()
    assert (src / "core_v1.py").is_file()
    assert (src / "apps_v1.py").is_file()
    assert (generated_package / "pyproject.toml").is_file()


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


def test_generated_imports_and_validates(
    generated_package: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Import the generated modules and exercise them against sample JSON."""
    src_root = str(generated_package / "src")
    monkeypatch.syspath_prepend(src_root)

    # Drop cached sibling modules from earlier runs (`tmp_path` differs per test).
    for mod in list(sys.modules):
        if mod.startswith("kubex.k8s.v1_30"):
            sys.modules.pop(mod, None)
    # `kubex.__path__` was set via extend_path when kubex was first imported;
    # at that point the tmp-path injection below hadn't happened yet, so we
    # re-extend it now.
    import kubex

    from pkgutil import extend_path

    kubex.__path__ = extend_path(list(kubex.__path__), kubex.__name__)

    core_v1 = importlib.import_module("kubex.k8s.v1_30.core_v1")
    apps_v1 = importlib.import_module("kubex.k8s.v1_30.apps_v1")

    Node = core_v1.Node
    NodeList = core_v1.NodeList
    Deployment = apps_v1.Deployment
    DeploymentList = apps_v1.DeploymentList

    # __RESOURCE_CONFIG__ is wired and carries correct scope.
    assert Node.__RESOURCE_CONFIG__.url() == "/api/v1/nodes"
    assert Node.__RESOURCE_CONFIG__.url(name="nd1") == "/api/v1/nodes/nd1"
    assert (
        Deployment.__RESOURCE_CONFIG__.url(namespace="ns1")
        == "/apis/apps/v1/namespaces/ns1/deployments"
    )

    # list_model is the pre-generated concrete class, not one built at access time.
    assert Node.__RESOURCE_CONFIG__.list_model is NodeList
    assert Deployment.__RESOURCE_CONFIG__.list_model is DeploymentList

    # Validate a real payload with acronym field round-trips via alias.
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
    # Enum is a real Enum class, not Literal.
    assert node.status.phase.value == "Running"
    # Round-trip preserves camelCase aliases.
    dumped = node.model_dump(by_alias=True, exclude_none=True)
    assert dumped["status"]["addresses"][0]["internalIP"] == "10.0.0.1"
    assert dumped["status"]["addresses"][0]["podIPs"] == ["10.0.0.1"]
    assert dumped["status"]["phase"] == "Running"

    # Cluster-scoped rejects a namespace argument.
    import pytest as _pytest

    with _pytest.raises(ValueError):
        Node.__RESOURCE_CONFIG__.url(namespace="x")

    # Deployment carries both HasStatusSubresource and HasScaleSubresource.
    from kubex_core.models.interfaces import HasScaleSubresource, HasStatusSubresource

    assert issubclass(Deployment, HasStatusSubresource)
    assert issubclass(Deployment, HasScaleSubresource)


def test_enum_placement_inline(generated_package: Path) -> None:
    """Single-use enums live inside the group module, not in _common.py."""
    src = generated_package / "src" / "kubex" / "k8s" / "v1_30"
    core = (src / "core_v1.py").read_text()
    apps = (src / "apps_v1.py").read_text()
    common = (src / "_common.py").read_text()

    # NodeStatus.phase → class NodeStatusPhase in core_v1.
    assert "class NodeStatusPhase(str, Enum):" in core
    # DeploymentCondition.type → class DeploymentConditionType in apps_v1.
    assert "class DeploymentConditionType(str, Enum):" in apps
    # Single-use enums stay out of _common.
    assert "class NodeStatusPhase" not in common
    assert "class DeploymentConditionType" not in common


def test_common_exports_intorstring(generated_package: Path) -> None:
    common = (
        generated_package / "src" / "kubex" / "k8s" / "v1_30" / "_common.py"
    ).read_text()
    assert "IntOrString = int | str" in common


def test_init_re_exports_index(generated_package: Path) -> None:
    init = (
        generated_package / "src" / "kubex" / "k8s" / "v1_30" / "__init__.py"
    ).read_text()
    assert "INDEX" in init
    assert "Node," in init or "Node\n" in init
    assert "Deployment," in init or "Deployment\n" in init
