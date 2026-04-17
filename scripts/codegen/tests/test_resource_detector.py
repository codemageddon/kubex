from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts.codegen.resource_detector import detect_resources

FIXTURE = Path(__file__).parent / "fixtures" / "mini_swagger.json"


def _load() -> dict[str, Any]:
    return json.loads(FIXTURE.read_text())  # type: ignore[no-any-return]


def test_detects_namespace_and_cluster_scope() -> None:
    spec = _load()
    resources = detect_resources(spec["definitions"], spec["paths"])
    kinds = {r.kind: r for r in resources if not r.kind.endswith("List")}
    assert "Deployment" in kinds
    assert "Node" in kinds
    assert kinds["Deployment"].is_namespaced is True
    assert kinds["Node"].is_namespaced is False


def test_detects_subresources() -> None:
    spec = _load()
    resources = detect_resources(spec["definitions"], spec["paths"])
    by_kind = {r.kind: r for r in resources}
    deployment = by_kind["Deployment"]
    assert deployment.has_status is True
    assert deployment.has_scale is True
    assert deployment.has_logs is False
    assert deployment.is_evictable is False
    node = by_kind["Node"]
    assert node.has_status is True
    assert node.has_scale is False


def test_plural_and_group_version() -> None:
    spec = _load()
    resources = detect_resources(spec["definitions"], spec["paths"])
    by_kind = {r.kind: r for r in resources if not r.kind.endswith("List")}
    assert by_kind["Deployment"].group == "apps"
    assert by_kind["Deployment"].version == "v1"
    assert by_kind["Deployment"].plural == "deployments"
    assert by_kind["Node"].group == "core"
    assert by_kind["Node"].plural == "nodes"


def test_list_definition_attached() -> None:
    spec = _load()
    resources = detect_resources(spec["definitions"], spec["paths"])
    by_kind = {r.kind: r for r in resources if not r.kind.endswith("List")}
    assert by_kind["Deployment"].list_definition == "io.k8s.api.apps.v1.DeploymentList"
    assert by_kind["Node"].list_definition == "io.k8s.api.core.v1.NodeList"
