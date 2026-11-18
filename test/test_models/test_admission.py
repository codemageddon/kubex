"""Tests for the admission.k8s.io/v1 AdmissionReview models."""

from __future__ import annotations

import base64
import json
from typing import Any, assert_type

import pytest
from pydantic import ValidationError

from kubex.core.patch import JsonPatch
from kubex.k8s.v1_35.core.v1.pod import Pod
from kubex_core.models.admission import AdmissionRequest, AdmissionReview

UID = "705ab4f5-6393-11e8-b7cc-42010a800002"


def _pod(name: str, image: str) -> dict[str, Any]:
    return {
        "apiVersion": "v1",
        "kind": "Pod",
        "metadata": {"name": name, "namespace": "default"},
        "spec": {"containers": [{"name": "app", "image": image}]},
    }


def _review(**request: Any) -> dict[str, Any]:
    return {
        "apiVersion": "admission.k8s.io/v1",
        "kind": "AdmissionReview",
        "request": {
            "uid": UID,
            "kind": {"group": "", "version": "v1", "kind": "Pod"},
            "resource": {"group": "", "version": "v1", "resource": "pods"},
            "namespace": "default",
            "operation": "CREATE",
            "userInfo": {
                "username": "admin",
                "uid": "014fbff9a07c",
                "groups": ["system:authenticated", "system:masters"],
                "extra": {"some-key": ["some-value1", "some-value2"]},
            },
            **request,
        },
    }


def _wire(review: AdmissionReview[Any]) -> dict[str, Any]:
    # How a webhook serializes its reply.
    result: dict[str, Any] = json.loads(
        review.model_dump_json(by_alias=True, exclude_none=True)
    )
    return result


def test_parse_create_request() -> None:
    raw = _review(
        name="web",
        object=_pod("web", "nginx:1.27"),
        oldObject=None,
        dryRun=False,
        options={"apiVersion": "meta.k8s.io/v1", "kind": "CreateOptions"},
        requestKind={"group": "", "version": "v1", "kind": "Pod"},
        requestResource={"group": "", "version": "v1", "resource": "pods"},
    )
    review = AdmissionReview[Pod].model_validate(raw)

    request = review.request
    assert request is not None
    assert request.uid == UID
    assert request.kind.group == ""
    assert request.kind.kind == "Pod"
    assert request.resource.resource == "pods"
    assert request.request_kind == request.kind
    assert request.operation == "CREATE"
    assert request.name == "web"
    assert request.namespace == "default"
    assert request.dry_run is False
    assert request.options == {"apiVersion": "meta.k8s.io/v1", "kind": "CreateOptions"}
    assert request.user_info.username == "admin"
    assert request.user_info.groups == ["system:authenticated", "system:masters"]
    assert request.user_info.extra == {"some-key": ["some-value1", "some-value2"]}
    assert isinstance(request.object, Pod)
    assert request.object.spec is not None
    assert request.object.spec.containers[0].image == "nginx:1.27"
    assert request.old_object is None
    assert review.response is None


def test_parse_update_of_subresource() -> None:
    raw = _review(
        name="web",
        operation="UPDATE",
        subResource="status",
        requestSubResource="status",
        object=_pod("web", "nginx:1.28"),
        oldObject=_pod("web", "nginx:1.27"),
    )
    request = AdmissionReview[Pod].model_validate(raw).request
    assert request is not None
    assert request.sub_resource == "status"
    assert request.request_sub_resource == "status"
    assert isinstance(request.old_object, Pod)
    assert request.old_object.spec is not None
    assert request.old_object.spec.containers[0].image == "nginx:1.27"


def test_parse_delete_request() -> None:
    raw = _review(
        name="web",
        operation="DELETE",
        oldObject=_pod("web", "nginx:1.27"),
        options={"apiVersion": "meta.k8s.io/v1", "kind": "DeleteOptions"},
    )
    request = AdmissionReview[Pod].model_validate(raw).request
    assert request is not None
    assert request.object is None
    assert isinstance(request.old_object, Pod)


def test_unparameterized_review_keeps_objects_as_dicts() -> None:
    # CONNECT requests carry an options object (here PodExecOptions), not a
    # resource, so it must not be forced through a resource model.
    exec_options = {
        "apiVersion": "v1",
        "kind": "PodExecOptions",
        "stdin": True,
        "command": ["sh"],
    }
    raw = _review(
        name="web",
        operation="CONNECT",
        subResource="exec",
        object=exec_options,
    )
    review: AdmissionReview[dict[str, Any]] = AdmissionReview.model_validate(raw)
    assert review.request is not None
    assert review.request.object == exec_options

    any_review = AdmissionReview[Any].model_validate(raw)
    assert any_review.request is not None
    assert any_review.request.object == exec_options


@pytest.mark.parametrize(
    ("kind", "obj"),
    [
        (
            {"group": "", "version": "v1", "kind": "Binding"},
            {
                "apiVersion": "v1",
                "kind": "Binding",
                "metadata": {"name": "web"},
                "target": {"kind": "Node", "name": "node-1"},
            },
        ),
        (
            {"group": "policy", "version": "v1", "kind": "Eviction"},
            {
                "apiVersion": "policy/v1",
                "kind": "Eviction",
                "metadata": {"name": "web"},
            },
        ),
    ],
)
def test_object_of_another_kind(kind: dict[str, str], obj: dict[str, Any]) -> None:
    # A webhook whose rules list pods/* receives pods/binding and
    # pods/eviction: a typed review fails as a whole, an untyped one parses.
    raw = _review(name="web", subResource=obj["kind"].lower(), kind=kind, object=obj)
    with pytest.raises(ValidationError):
        AdmissionReview[Pod].model_validate(raw)

    request = AdmissionReview[dict[str, Any]].model_validate(raw).request
    assert request is not None
    assert request.uid == UID
    assert request.object == obj


def test_unknown_fields_round_trip() -> None:
    raw = _review(name="web", object=_pod("web", "nginx"), futureField={"a": 1})
    raw["futureTopLevel"] = "x"
    review = AdmissionReview[dict[str, Any]].model_validate(raw)
    assert _wire(review) == raw


def test_rejects_other_review_versions() -> None:
    raw = _review(object=_pod("web", "nginx"))
    raw["apiVersion"] = "admission.k8s.io/v1beta1"
    with pytest.raises(ValidationError):
        AdmissionReview[Pod].model_validate(raw)


def _request() -> AdmissionRequest[Pod]:
    request = (
        AdmissionReview[Pod]
        .model_validate(_review(object=_pod("web", "nginx")))
        .request
    )
    assert request is not None
    return request


def test_allow() -> None:
    reply = AdmissionReview[Pod](response=_request().allow())
    assert _wire(reply) == {
        "apiVersion": "admission.k8s.io/v1",
        "kind": "AdmissionReview",
        "response": {"uid": UID, "allowed": True},
    }


def test_allow_with_warnings_and_audit_annotations() -> None:
    response = _request().allow(
        warnings=["image tag is not pinned"], audit_annotations={"checked": "true"}
    )
    assert _wire(AdmissionReview[Pod](response=response))["response"] == {
        "uid": UID,
        "allowed": True,
        "warnings": ["image tag is not pinned"],
        "auditAnnotations": {"checked": "true"},
    }


@pytest.mark.parametrize("as_bytes", [False, True])
def test_allow_with_patch(as_bytes: bool) -> None:
    patch_text = JsonPatch().add("/metadata/labels", {"team": "a"}).serialize()
    patch = patch_text.encode() if as_bytes else patch_text
    response = _request().allow(patch=patch)
    assert response.patch == patch_text.encode()
    assert response.patch_type == "JSONPatch"

    wire = _wire(AdmissionReview[Pod](response=response))["response"]
    assert wire["patchType"] == "JSONPatch"
    assert json.loads(base64.b64decode(wire["patch"])) == [
        {"op": "add", "path": "/metadata/labels", "value": {"team": "a"}}
    ]


@pytest.mark.parametrize("patch", ["", b""])
def test_allow_with_empty_patch_sends_no_patch(patch: str | bytes) -> None:
    response = _request().allow(patch=patch)
    assert response.patch is None
    assert response.patch_type is None
    assert _wire(AdmissionReview[Pod](response=response))["response"] == {
        "uid": UID,
        "allowed": True,
    }


def test_patch_is_decoded_from_the_wire() -> None:
    patch = b'[{"op":"remove","path":"/spec/hostNetwork"}]'
    raw = {
        "apiVersion": "admission.k8s.io/v1",
        "kind": "AdmissionReview",
        "response": {
            "uid": UID,
            "allowed": True,
            "patch": base64.b64encode(patch).decode(),
            "patchType": "JSONPatch",
        },
    }
    review = AdmissionReview[Any].model_validate_json(json.dumps(raw))
    assert review.response is not None
    assert review.response.patch == patch
    assert _wire(review) == raw
    # Python-mode dumps keep the bytes.
    assert review.response.model_dump()["patch"] == patch


def test_patch_rejects_non_base64_text() -> None:
    raw = {
        "response": {"uid": UID, "allowed": True, "patch": '[{"op":"remove"}]'},
    }
    with pytest.raises(ValidationError, match="base64"):
        AdmissionReview[Any].model_validate(raw)


def test_deny() -> None:
    response = _request().deny("privileged pods are not allowed")
    assert _wire(AdmissionReview[Pod](response=response))["response"] == {
        "uid": UID,
        "allowed": False,
        "status": {
            "apiVersion": "v1",
            "kind": "Status",
            "metadata": {},
            "status": "Failure",
            "code": 403,
            "message": "privileged pods are not allowed",
        },
    }


def test_deny_with_code_reason_and_warnings() -> None:
    response = _request().deny(
        "quota exceeded",
        code=429,
        reason="TooManyRequests",
        warnings=["retry later"],
        audit_annotations={"quota": "exceeded"},
    )
    assert response.allowed is False
    assert response.status is not None
    assert response.status.code == 429
    assert response.status.reason == "TooManyRequests"
    assert response.warnings == ["retry later"]
    assert response.audit_annotations == {"quota": "exceeded"}
    assert response.patch is None
    assert response.patch_type is None


def test_object_types() -> None:
    raw = _review(object=_pod("web", "nginx"))
    typed = AdmissionReview[Pod].model_validate(raw)
    assert typed.request is not None
    assert_type(typed.request.object, Pod | None)
    assert_type(typed.request.old_object, Pod | None)
