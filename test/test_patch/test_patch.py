from __future__ import annotations

import json

from pydantic import BaseModel

from kubex.core.patch import ApplyPatch, MergePatch, StrategicMergePatch


class _Spec(BaseModel):
    replicas: int | None = None
    name: str | None = None


class _Resource(BaseModel):
    spec: _Spec | None = None


def test_merge_patch_default_preserves_explicit_null() -> None:
    """RFC 7396: an explicit null must reach the server to delete the field."""
    patch = MergePatch(_Resource(spec=_Spec(replicas=None)))
    result = json.loads(patch.serialize(by_alias=True, exclude_unset=True))
    assert result == {"spec": {"replicas": None}}


def test_merge_patch_no_args_default_preserves_explicit_null() -> None:
    """patch_subresource()/patch_metadata() call serialize() with no arguments."""
    patch = MergePatch(_Resource(spec=_Spec(replicas=None)))
    result = json.loads(patch.serialize())
    assert result == {"spec": {"replicas": None}}


def test_merge_patch_omitted_field_still_excluded() -> None:
    """A field the caller never touched stays distinguishable from an explicit null."""
    patch = MergePatch(_Resource(spec=_Spec(replicas=5)))
    result = json.loads(patch.serialize(by_alias=True, exclude_unset=True))
    assert result == {"spec": {"replicas": 5}}
    assert "name" not in result["spec"]


def test_merge_patch_explicit_exclude_none_true_still_available() -> None:
    """Callers can still opt back into the old (null-dropping) behavior explicitly."""
    patch = MergePatch(_Resource(spec=_Spec(replicas=None)))
    result = json.loads(
        patch.serialize(by_alias=True, exclude_unset=True, exclude_none=True)
    )
    assert result == {"spec": {}}


def test_strategic_merge_patch_default_preserves_explicit_null() -> None:
    patch = StrategicMergePatch(_Resource(spec=_Spec(replicas=None)))
    result = json.loads(patch.serialize(by_alias=True, exclude_unset=True))
    assert result == {"spec": {"replicas": None}}


def test_apply_patch_default_still_drops_none() -> None:
    """ApplyPatch intentionally keeps exclude_none=True (SSA has no null-delete convention)."""
    patch = ApplyPatch(_Resource(spec=_Spec(replicas=None)))
    result = patch.serialize(by_alias=True, exclude_unset=True)
    assert "replicas" not in result
