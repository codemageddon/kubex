"""Derive resource scope and subresource capabilities from `spec.paths`.

Each definition that carries `x-kubernetes-group-version-kind` and appears on
a collection path is classified as a Kubernetes resource. Walking the path
strings tells us:

- scope (namespace vs cluster) from the presence of `/namespaces/{namespace}/`
- subresources (`/status`, `/scale`, `/log`, `/eviction`, `/ephemeralcontainers`,
  `/resize`, `/attach`, `/exec`, `/portforward`) from path suffixes
- plural name from the terminal path segment
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ResourceInfo:
    """Collected runtime metadata for one Kubernetes resource definition."""

    definition: str  # swagger definition name
    group: str
    version: str
    kind: str
    plural: str
    is_namespaced: bool
    has_status: bool = False
    has_scale: bool = False
    has_logs: bool = False
    is_evictable: bool = False
    has_ephemeral_containers: bool = False
    has_resize: bool = False
    has_attach: bool = False
    has_exec: bool = False
    has_port_forward: bool = False
    list_definition: str | None = (
        None  # swagger definition name of the paired *List, if any
    )


_NAMESPACED_COLLECTION = re.compile(
    r"^/api(?:s/(?P<group>[^/]+))?/(?P<version>v[0-9a-z]+)/namespaces/\{namespace\}/(?P<plural>[^/{}]+)(?P<tail>/.*)?$"
)
_CLUSTER_COLLECTION = re.compile(
    r"^/api(?:s/(?P<group>[^/]+))?/(?P<version>v[0-9a-z]+)/(?P<plural>[^/{}]+)(?P<tail>/.*)?$"
)

_SUBRESOURCE_FLAGS: dict[str, str] = {
    "/status": "has_status",
    "/scale": "has_scale",
    "/log": "has_logs",
    "/eviction": "is_evictable",
    "/ephemeralcontainers": "has_ephemeral_containers",
    "/resize": "has_resize",
    "/attach": "has_attach",
    "/exec": "has_exec",
    "/portforward": "has_port_forward",
}


def detect_resources(
    definitions: dict[str, dict[str, Any]],
    paths: dict[str, dict[str, Any]],
) -> list[ResourceInfo]:
    """Return the list of resource descriptors derived from the spec.

    Pure function: reads only from the inputs, no I/O.
    """
    # 1) Index definitions by (group, version, kind) via x-kubernetes-group-version-kind.
    by_gvk: dict[tuple[str, str, str], str] = {}
    for name, schema in definitions.items():
        gvks = schema.get("x-kubernetes-group-version-kind") or []
        for gvk in gvks:
            group = gvk.get("group") or "core"
            version = gvk.get("version")
            kind = gvk.get("kind")
            if not (version and kind):
                continue
            by_gvk[(group, version, kind)] = name

    # 2) Walk paths to learn scope/plural/subresources, keyed by (group, version, kind).
    discovered: dict[tuple[str, str, str], ResourceInfo] = {}
    by_plural: dict[tuple[str, str, str], tuple[str, str, str]] = {}
    pending_flags: dict[tuple[str, str, str], set[str]] = {}

    for path, ops in paths.items():
        _collect_subresource_flags(path, pending_flags)

        info = _scan_path(path, ops, by_gvk=by_gvk)
        if info is None:
            continue
        key = (info.group, info.version, info.kind)
        existing = discovered.get(key)
        if existing is None:
            discovered[key] = info
            by_plural[(info.group, info.version, info.plural)] = key
        else:
            existing.is_namespaced = existing.is_namespaced or info.is_namespaced
            existing.has_status = existing.has_status or info.has_status
            existing.has_scale = existing.has_scale or info.has_scale
            existing.has_logs = existing.has_logs or info.has_logs
            existing.is_evictable = existing.is_evictable or info.is_evictable
            existing.has_ephemeral_containers = (
                existing.has_ephemeral_containers or info.has_ephemeral_containers
            )
            existing.has_resize = existing.has_resize or info.has_resize
            existing.has_attach = existing.has_attach or info.has_attach
            existing.has_exec = existing.has_exec or info.has_exec
            existing.has_port_forward = (
                existing.has_port_forward or info.has_port_forward
            )

    # Apply subresource flags detected from path structure to parent resources.
    # This handles cases where the subresource endpoint's GVK refers to a
    # different kind (e.g. /scale -> "Scale", /eviction -> "Eviction") and
    # _scan_path could not match it to the parent resource.
    for (group, version, plural), flags in pending_flags.items():
        parent_key = by_plural.get((group, version, plural))
        if parent_key is None:
            continue
        parent = discovered[parent_key]
        for flag in flags:
            setattr(parent, flag, True)

    # 3) Attach paired *List definitions where they exist.
    for info in discovered.values():
        list_def = f"{_definition_prefix(info.definition)}.{info.kind}List"
        if list_def in definitions:
            info.list_definition = list_def

    return sorted(discovered.values(), key=lambda r: (r.group, r.version, r.kind))


def _collect_subresource_flags(
    path: str,
    pending: dict[tuple[str, str, str], set[str]],
) -> None:
    """Detect subresource flags purely from path structure.

    Stores them keyed by ``(group, version, plural)`` so they can be
    applied to the parent resource after the main discovery loop, even
    when the endpoint's GVK refers to a different kind (e.g. ``Scale``).
    """
    m = _NAMESPACED_COLLECTION.match(path) or _CLUSTER_COLLECTION.match(path)
    if m is None:
        return
    group = m.groupdict().get("group") or "core"
    version = m["version"]
    plural = m["plural"]
    tail = m.groupdict().get("tail") or ""
    trimmed = _strip_name(tail)
    for suffix, flag in _SUBRESOURCE_FLAGS.items():
        if trimmed == suffix:
            pending.setdefault((group, version, plural), set()).add(flag)
            return


def _scan_path(
    path: str,
    ops: dict[str, Any],
    *,
    by_gvk: dict[tuple[str, str, str], str],
) -> ResourceInfo | None:
    """Match one path. Returns the resource record, or None when not a resource collection."""
    m = _NAMESPACED_COLLECTION.match(path) or _CLUSTER_COLLECTION.match(path)
    if m is None:
        return None
    is_namespaced = "/namespaces/{namespace}/" in path
    group = m.groupdict().get("group") or "core"
    version = m["version"]
    plural = m["plural"]
    tail = m.groupdict().get("tail") or ""

    subresource_flags: dict[str, bool] = {
        attr: False for attr in _SUBRESOURCE_FLAGS.values()
    }
    # Trim a leading /{name} and check for a subresource segment.
    trimmed = _strip_name(tail)
    for suffix, flag in _SUBRESOURCE_FLAGS.items():
        if trimmed == suffix:
            subresource_flags[flag] = True
            break

    kind = _kind_from_operations(ops)
    if kind is None:
        return None
    key = (group, version, kind)
    definition = by_gvk.get(key)
    if definition is None:
        return None
    return ResourceInfo(
        definition=definition,
        group=group,
        version=version,
        kind=kind,
        plural=plural,
        is_namespaced=is_namespaced,
        has_status=subresource_flags["has_status"],
        has_scale=subresource_flags["has_scale"],
        has_logs=subresource_flags["has_logs"],
        is_evictable=subresource_flags["is_evictable"],
        has_ephemeral_containers=subresource_flags["has_ephemeral_containers"],
        has_resize=subresource_flags["has_resize"],
        has_attach=subresource_flags["has_attach"],
        has_exec=subresource_flags["has_exec"],
        has_port_forward=subresource_flags["has_port_forward"],
    )


def _strip_name(tail: str) -> str:
    """Remove a leading `/{name}` segment if present."""
    if tail.startswith("/{") and "}" in tail:
        end = tail.index("}")
        return tail[end + 1 :]
    return tail


def _kind_from_operations(ops: dict[str, Any]) -> str | None:
    """Pull the kind from an operation's `x-kubernetes-group-version-kind` hint."""
    for op in ops.values():
        if not isinstance(op, dict):
            continue
        gvk = op.get("x-kubernetes-group-version-kind")
        if isinstance(gvk, dict) and "kind" in gvk:
            return str(gvk["kind"])
    return None


def _definition_prefix(name: str) -> str:
    """`io.k8s.api.core.v1.Pod` -> `io.k8s.api.core.v1`."""
    return name.rsplit(".", 1)[0]


@dataclass
class DetectionSummary:
    """Summary returned by `detect_resources_with_stats` — handy for logging."""

    resources: list[ResourceInfo] = field(default_factory=list)
    unmatched_paths: list[str] = field(default_factory=list)


def detect_resources_with_stats(
    definitions: dict[str, dict[str, Any]],
    paths: dict[str, dict[str, Any]],
) -> DetectionSummary:
    """Like `detect_resources`, plus a list of paths that didn't match any resource."""
    resources = detect_resources(definitions, paths)
    matched_definitions = {r.definition for r in resources}
    unmatched: list[str] = []
    for path in paths:
        m = _NAMESPACED_COLLECTION.match(path) or _CLUSTER_COLLECTION.match(path)
        if m is None:
            unmatched.append(path)
            continue
        kind = _kind_from_operations(paths[path])
        if kind is None:
            unmatched.append(path)
            continue
        group = m.groupdict().get("group") or "core"
        version = m["version"]
        defn = f"io.k8s.api.{group}.{version}.{kind}"
        if defn not in matched_definitions:
            unmatched.append(path)
    return DetectionSummary(resources=resources, unmatched_paths=unmatched)
