"""admission.k8s.io/v1 `AdmissionReview`: what the API server sends to an
admission webhook, and what the webhook sends back.

The API server never serves these types, so they are not in the OpenAPI spec
and are hand-written here instead of generated.

`AdmissionReview` and `AdmissionRequest` are generic over the type of
`request.object` / `request.oldObject`. Left unparameterized (or
`AdmissionReview[dict[str, Any]]`) they stay plain dicts, and the review parses
whatever the API server sends, including `CONNECT` requests, whose object is an
options type such as `PodExecOptions`. `AdmissionReview[Pod]` validates them as
`Pod`, but an object that does not fit (another kind, such as the `Binding` of
`pods/binding`) fails the whole parse: the webhook never gets `request.uid`,
cannot answer, and the API server applies the webhook's `failurePolicy`. So
parse untyped and validate the object yourself.

A webhook parses the request body, builds a response with
`AdmissionRequest.allow()` or `AdmissionRequest.deny()` (both copy the
request's `uid`, which the API server requires) and returns it wrapped in a new
review::

    from typing import Any

    from pydantic import ValidationError

    from kubex.k8s.v1_35.core.v1.pod import Pod
    from kubex_core.models.admission import AdmissionReview


    def review_pod(body: bytes) -> str:
        review = AdmissionReview[dict[str, Any]].model_validate_json(body)
        request = review.request
        assert request is not None
        kind = request.kind
        if (kind.group, kind.kind) != ("", "Pod") or request.object is None:
            response = request.allow()  # e.g. pods/binding, or a DELETE
        else:
            try:
                pod = Pod.model_validate(request.object)
            except ValidationError:
                response = request.deny("invalid Pod")
            else:
                if pod.spec and pod.spec.host_network:
                    response = request.deny("hostNetwork is not allowed")
                else:
                    response = request.allow()
        reply = AdmissionReview[dict[str, Any]](response=response)
        return reply.model_dump_json(by_alias=True, exclude_none=True)

Only `admission.k8s.io/v1` is supported: list `"v1"` in the webhook
configuration's `admissionReviewVersions`.
"""

from __future__ import annotations

import base64
import binascii
from typing import Annotated, Any, Generic, Literal, TypeVar

from pydantic import BeforeValidator, PlainSerializer

from .base import BaseK8sModel
from .status import Status

__all__ = [
    "AdmissionRequest",
    "AdmissionResponse",
    "AdmissionReview",
    "GroupVersionKind",
    "GroupVersionResource",
    "Operation",
    "PatchType",
    "UserInfo",
]

ObjectType = TypeVar("ObjectType")
"""Type of `AdmissionRequest.object` and `AdmissionRequest.old_object`."""

Operation = Literal["CREATE", "UPDATE", "DELETE", "CONNECT"]
"""The operation being admitted. A patch may be admitted as `CREATE` or `UPDATE`."""

PatchType = Literal["JSONPatch"]
"""The only patch type the API server accepts from a webhook."""


def _decode_base64(value: Any) -> Any:
    # A str is the wire form (a Go []byte marshals as base64); bytes are
    # already decoded.
    if not isinstance(value, str):
        return value
    try:
        return base64.b64decode(value, validate=True)
    except binascii.Error as e:
        raise ValueError(f"expected base64-encoded data: {e}") from e


def _encode_base64(value: Any) -> Any:
    if not isinstance(value, bytes):
        return value
    return base64.b64encode(value).decode("ascii")


_Base64Bytes = Annotated[
    bytes,
    BeforeValidator(_decode_base64),
    PlainSerializer(_encode_base64, return_type=str, when_used="json"),
]


class GroupVersionKind(BaseK8sModel):
    """Identifies a kind. `group` is empty for the core API group."""

    group: str = ""
    version: str
    kind: str


class GroupVersionResource(BaseK8sModel):
    """Identifies a resource. `group` is empty for the core API group."""

    group: str = ""
    version: str
    resource: str


class UserInfo(BaseK8sModel):
    """authentication.k8s.io/v1 UserInfo: the user that made the request."""

    username: str | None = None
    """The name that uniquely identifies this user among all active users."""
    uid: str | None = None
    """A unique value that identifies this user across time."""
    groups: list[str] | None = None
    """The names of groups this user is a part of."""
    extra: dict[str, list[str]] | None = None
    """Any additional information provided by the authenticator."""


class AdmissionRequest(BaseK8sModel, Generic[ObjectType]):
    """The attributes of the request being admitted."""

    uid: str
    """Identifies this request/response round trip between the API server and
    the webhook (not the user's request). Copy it into the response."""
    kind: GroupVersionKind
    """The fully-qualified type of `object`, e.g. `v1.Pod` or `autoscaling.v1.Scale`."""
    resource: GroupVersionResource
    """The fully-qualified resource being requested, e.g. `v1.pods`."""
    sub_resource: str | None = None
    """The subresource being requested, if any, e.g. `status` or `scale`."""
    request_kind: GroupVersionKind | None = None
    """The type of the original API request. Differs from `kind` when the
    request was converted to match the webhook's rules (`matchPolicy: Equivalent`)."""
    request_resource: GroupVersionResource | None = None
    """The resource of the original API request; see `request_kind`."""
    request_sub_resource: str | None = None
    """The subresource of the original API request; see `request_kind`."""
    name: str | None = None
    """The name of the object. Empty on a `CREATE` that relies on `generateName`."""
    namespace: str | None = None
    """The namespace of the request, if any."""
    operation: Operation
    """The operation being performed; may differ from the one requested
    (a patch can be admitted as `CREATE` or `UPDATE`)."""
    user_info: UserInfo
    """The user that made the request."""
    object: ObjectType | None = None
    """The object from the incoming request. `None` for `DELETE`."""
    old_object: ObjectType | None = None
    """The existing object. Only set for `UPDATE` and `DELETE`."""
    dry_run: bool | None = None
    """When true, the change will not be persisted, so a webhook with side
    effects must not apply them."""
    options: dict[str, Any] | None = None
    """The options of the operation performed, e.g. `meta.k8s.io/v1`
    `CreateOptions`, `UpdateOptions` or `DeleteOptions`."""

    def allow(
        self,
        *,
        patch: str | bytes | None = None,
        warnings: list[str] | None = None,
        audit_annotations: dict[str, str] | None = None,
    ) -> AdmissionResponse:
        """Admit the request, optionally changing the object.

        `patch` is an RFC 6902 JSON Patch document against `object`, as JSON
        text (e.g. `JsonPatch(...).serialize()`); it is base64-encoded on the
        wire. Only mutating webhooks may return one. An empty `patch` is sent
        as no patch.
        """
        if isinstance(patch, str):
            patch = patch.encode()
        if not patch:
            # The API server fails a response that has a patchType but an
            # empty patch.
            patch = None
        return AdmissionResponse(
            uid=self.uid,
            allowed=True,
            patch=patch,
            patch_type="JSONPatch" if patch is not None else None,
            warnings=warnings,
            audit_annotations=audit_annotations,
        )

    def deny(
        self,
        message: str,
        *,
        code: int = 403,
        reason: str | None = None,
        warnings: list[str] | None = None,
        audit_annotations: dict[str, str] | None = None,
    ) -> AdmissionResponse:
        """Reject the request.

        The client sees `message` after `admission webhook "<name>" denied the
        request: `, with HTTP status `code`; the API server raises a code below
        400 to 400.
        """
        return AdmissionResponse(
            uid=self.uid,
            allowed=False,
            status=Status(status="Failure", code=code, message=message, reason=reason),
            warnings=warnings,
            audit_annotations=audit_annotations,
        )


class AdmissionResponse(BaseK8sModel):
    """The webhook's decision."""

    uid: str
    """Must be copied from `AdmissionRequest.uid`."""
    allowed: bool
    """Whether the request is admitted."""
    status: Status | None = None
    """Why the request was denied. Not consulted when `allowed` is true."""
    patch: _Base64Bytes | None = None
    """An RFC 6902 JSON Patch document to apply to the object (mutating
    webhooks only). Raw bytes here; base64 on the wire."""
    patch_type: PatchType | None = None
    """Required when `patch` is set."""
    audit_annotations: dict[str, str] | None = None
    """Added to the audit log of the request, each key prefixed with the
    webhook's name."""
    warnings: list[str] | None = None
    """Warning messages returned to the API client. Keep each under 120 characters."""


class AdmissionReview(BaseK8sModel, Generic[ObjectType]):
    """The admission webhook request (`request`) or reply (`response`)."""

    api_version: Literal["admission.k8s.io/v1"] = "admission.k8s.io/v1"
    kind: Literal["AdmissionReview"] = "AdmissionReview"
    request: AdmissionRequest[ObjectType] | None = None
    """Set by the API server."""
    response: AdmissionResponse | None = None
    """Set by the webhook."""
