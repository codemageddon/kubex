# Admission Webhooks

An [admission webhook](https://kubernetes.io/docs/reference/access-authn-authz/extensible-admission-controllers/) is an HTTPS endpoint the API server calls before it persists an object. The API server POSTs an `AdmissionReview` with a `request`, and the webhook answers with an `AdmissionReview` carrying a `response`. A validating webhook admits or rejects the object. A mutating webhook can also send back a JSON Patch.

`kubex_core.models.admission` provides the `admission.k8s.io/v1` types.

!!! note "What else a webhook needs"
    The models only parse the request and build the reply. To run a webhook you also need:

    - **An HTTPS server.** Kubex does not ship one: call the handler from the server you use (aiohttp, Starlette, ...). The API server only connects to webhooks over HTTPS.
    - **A TLS certificate** for the host name the API server connects to, listed as a subject alternative name: `<service>.<namespace>.svc` for a webhook behind a Service. The API server verifies it against the CA in the webhook configuration's `clientConfig.caBundle`, or against its system trust roots when that is empty. [cert-manager](https://cert-manager.io/docs/concepts/ca-injector/) can issue the certificate and fill in `caBundle`.
    - **A registration**: a `ValidatingWebhookConfiguration` or `MutatingWebhookConfiguration` that points at the server (`clientConfig.service` or `clientConfig.url`) and sets the `rules` that select the requests it gets, `admissionReviewVersions`, `sideEffects`, `failurePolicy` and `timeoutSeconds`. These are ordinary cluster resources: apply them with `kubectl`, or create them with `Api` and the models in `kubex.k8s.v1_35.admissionregistration.v1`.
    - **A network path from the API server** to the server, usually a Service in front of the webhook's pods. Network policies and, on managed clusters, firewall rules between the control plane and the nodes must allow it.

    With `failurePolicy: Fail`, matching requests are rejected while the webhook is down or unreachable. Exclude the webhook's own namespace with a `namespaceSelector`, so that its pods can still be created.

## Handling a review

Parse the body untyped first, as `AdmissionReview[dict[str, Any]]`. That parses any request the API server sends, so the webhook always gets `request.uid` and can answer. Then check `request.kind` and validate `request.object` as the model you expect. `request.allow()` and `request.deny()` build the `AdmissionResponse` and copy the request's `uid` into it, which the API server requires:

```python
from typing import Any

from pydantic import ValidationError

from kubex.k8s.v1_35.core.v1.pod import Pod
from kubex_core.models.admission import (
    AdmissionRequest,
    AdmissionResponse,
    AdmissionReview,
)


def review_pod(body: bytes) -> str:
    review = AdmissionReview[dict[str, Any]].model_validate_json(body)
    request = review.request
    assert request is not None

    reply = AdmissionReview[dict[str, Any]](response=check_pod(request))
    return reply.model_dump_json(by_alias=True, exclude_none=True)


def check_pod(request: AdmissionRequest[dict[str, Any]]) -> AdmissionResponse:
    # Rules listing subresources (`pods/*`, `*/*`) send requests such as
    # pods/binding and pods/eviction, whose object is a Binding or an
    # Eviction; `pods/*` alone does not match Pods themselves. The object is
    # None for DELETE.
    kind = request.kind
    if (kind.group, kind.kind) != ("", "Pod") or request.object is None:
        return request.allow()
    try:
        pod = Pod.model_validate(request.object)
    except ValidationError as e:
        # Fails closed; return request.allow() to fail open instead.
        return request.deny(f"invalid Pod: {e.error_count()} validation errors")

    spec = pod.spec
    security_contexts = (
        [c.security_context for c in spec.containers]
        + [c.security_context for c in spec.init_containers or []]
        + [c.security_context for c in spec.ephemeral_containers or []]
        if spec
        else []
    )
    if any(sc and sc.privileged for sc in security_contexts):
        return request.deny("privileged containers are not allowed")
    return request.allow()
```

The reply must be sent with `Content-Type: application/json`.

`deny()` sets a `Status` with `code` (default `403`) and `message`. The client sees `admission webhook "<name>" denied the request: <message>`. Both methods also take `warnings` (returned to the client) and `audit_annotations` (added to the request's audit event).

## Typed reviews

`AdmissionReview` and `AdmissionRequest` are generic over the type of `request.object` and `request.old_object`, so `AdmissionReview[Pod]` validates them as `Pod` in the same parse:

```python
review = AdmissionReview[Pod].model_validate_json(body)
```

!!! warning "A typed review fails as a whole"
    If `request.object` or `request.old_object` does not fit the model, the whole parse raises `ValidationError`, so the webhook never gets `request.uid` and cannot answer. The API server then applies the webhook's `failurePolicy`: `Fail` rejects the request, and `Ignore` admits it unchecked. This happens with an object of another kind, such as the `Binding` of `pods/binding`. It also happens when the model is stricter than the API server: a mutating webhook runs before the API server validates the object, and `old_object` is whatever was stored, possibly under an older CRD schema. Use a typed review only when the webhook's rules match that one kind and the model accepts every object the API server can send for it.

## Mutating

Pass an RFC 6902 JSON Patch document against `request.object` to `allow(patch=...)`. It takes JSON text or bytes, so `JsonPatch(...).serialize()` works directly. `allow()` sets `patchType: JSONPatch`, and the patch is base64-encoded on the wire:

```python
from kubex.core.patch import JsonPatch

patch = JsonPatch().add("/metadata/labels/admitted-by", "my-webhook")
response = request.allow(patch=patch.serialize())
```

A JSON Patch `add` fails when its parent path is missing, so check that `metadata.labels` exists before adding to it. Otherwise add the whole `/metadata/labels` map.

## Objects that are not resources

A webhook registered for `CONNECT` operations receives an options type such as `PodExecOptions` as `request.object`, not a resource. `request.options` is always a plain dict. Use `request.kind` (the `GroupVersionKind` of `object`) and `request.sub_resource` to tell the cases apart.

## Review versions

Only `admission.k8s.io/v1` is supported: list `"v1"` in the webhook configuration's `admissionReviewVersions`. A `v1beta1` review fails validation instead of being answered in the wrong version.
