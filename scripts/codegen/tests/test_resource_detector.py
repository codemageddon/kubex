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


def _pod_spec() -> tuple[dict[str, Any], dict[str, Any]]:
    """Build minimal definitions + paths for a Pod with all subresource paths."""
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
        "x-kubernetes-group-version-kind": {"group": "", "kind": "Pod", "version": "v1"}
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
    return definitions, paths


def test_detects_ephemeral_containers_flag() -> None:
    definitions, paths = _pod_spec()
    resources = detect_resources(definitions, paths)
    pod = next(r for r in resources if r.kind == "Pod")
    assert pod.has_ephemeral_containers is True


def test_detects_resize_flag() -> None:
    definitions, paths = _pod_spec()
    resources = detect_resources(definitions, paths)
    pod = next(r for r in resources if r.kind == "Pod")
    assert pod.has_resize is True


def test_detects_attach_flag() -> None:
    definitions, paths = _pod_spec()
    resources = detect_resources(definitions, paths)
    pod = next(r for r in resources if r.kind == "Pod")
    assert pod.has_attach is True


def test_detects_exec_flag() -> None:
    definitions, paths = _pod_spec()
    resources = detect_resources(definitions, paths)
    pod = next(r for r in resources if r.kind == "Pod")
    assert pod.has_exec is True


def test_detects_port_forward_flag() -> None:
    definitions, paths = _pod_spec()
    resources = detect_resources(definitions, paths)
    pod = next(r for r in resources if r.kind == "Pod")
    assert pod.has_port_forward is True


def test_new_flags_false_when_subresources_absent() -> None:
    """Resources without the new subresource paths have False flags."""
    spec = _load()
    resources = detect_resources(spec["definitions"], spec["paths"])
    deployment = next(r for r in resources if r.kind == "Deployment")
    assert deployment.has_ephemeral_containers is False
    assert deployment.has_resize is False
    assert deployment.has_attach is False
    assert deployment.has_exec is False
    assert deployment.has_port_forward is False


def test_all_pod_subresource_flags() -> None:
    """Pod should have all subresource flags set."""
    definitions, paths = _pod_spec()
    resources = detect_resources(definitions, paths)
    pod = next(r for r in resources if r.kind == "Pod")
    assert pod.has_status is True
    assert pod.has_logs is True
    assert pod.is_evictable is True
    assert pod.has_ephemeral_containers is True
    assert pod.has_resize is True
    assert pod.has_attach is True
    assert pod.has_exec is True
    assert pod.has_port_forward is True
