from __future__ import annotations

import pytest

from kubex.core.exceptions import KubexApiError, NotFound
from kubex.core.watch_event import EventType, WatchEvent
from kubex.k8s.v1_35.core.v1.pod import Pod
from kubex_core.models.status import Status


def _error_event(obj: dict[str, object]) -> dict[str, object]:
    return {"type": "ERROR", "object": obj}


def test_watch_event_error_with_code_and_reason_raises_matching_exception() -> None:
    event = _error_event(
        {
            "apiVersion": "v1",
            "kind": "Status",
            "metadata": {},
            "status": "Failure",
            "code": 404,
            "reason": "NotFound",
            "message": 'pods "my-pod" not found',
        }
    )
    with pytest.raises(NotFound) as exc_info:
        WatchEvent(Pod, event)
    assert isinstance(exc_info.value.content, Status)
    assert exc_info.value.content.message == 'pods "my-pod" not found'
    assert exc_info.value.content.reason == "NotFound"


def test_watch_event_error_without_code_or_reason_does_not_raise_validation_error() -> (
    None
):
    """A watch ERROR frame with StatusReasonUnknown (empty reason, no code) is
    valid per upstream metav1.Status, where both fields are omitempty. It must
    surface as a KubexApiError, not blow up while parsing the frame."""
    event = _error_event(
        {
            "apiVersion": "v1",
            "kind": "Status",
            "metadata": {},
            "status": "Failure",
            "message": "unknown error watching resource",
        }
    )
    with pytest.raises(KubexApiError) as exc_info:
        WatchEvent(Pod, event)
    assert isinstance(exc_info.value.content, Status)
    assert exc_info.value.content.code == 0
    assert exc_info.value.content.reason is None
    assert exc_info.value.content.message == "unknown error watching resource"


def test_watch_event_error_preserves_details() -> None:
    event = _error_event(
        {
            "apiVersion": "v1",
            "kind": "Status",
            "metadata": {},
            "status": "Failure",
            "code": 410,
            "reason": "Expired",
            "message": "too old resource version",
            "details": {"causes": [{"message": "resource version too old"}]},
        }
    )
    with pytest.raises(KubexApiError) as exc_info:
        WatchEvent(Pod, event)
    assert isinstance(exc_info.value.content, Status)
    assert exc_info.value.content.details is not None
    assert exc_info.value.content.details.causes is not None
    assert (
        exc_info.value.content.details.causes[0].message == "resource version too old"
    )


def test_watch_event_error_with_sparse_status_still_validates() -> None:
    """`status` and `StatusCause.message` are optional, matching upstream
    metav1.Status/StatusCause (both fields are `omitempty`). A frame that omits
    them — as an aggregated API server, admission webhook, or proxy might send —
    must still validate and surface its real `code`, not fall back to a
    fabricated `HTTPStatus(0)`."""
    event = _error_event({"apiVersion": "v1", "kind": "Status", "metadata": {}})
    with pytest.raises(KubexApiError) as exc_info:
        WatchEvent(Pod, event)
    assert isinstance(exc_info.value.content, Status)
    assert exc_info.value.content.status is None
    assert exc_info.value.content.code == 0


def test_watch_event_error_with_malformed_status_does_not_raise_validation_error() -> (
    None
):
    """An ERROR frame that isn't a valid Status at all (e.g. `status` set to a
    value outside the `Success`/`Failure` literal) must not escape as a
    pydantic.ValidationError — it should still surface as a KubexApiError,
    matching the guard pattern used everywhere else the codebase parses a
    Status (handle_request_error, Api.delete, _read_loop)."""
    event = _error_event(
        {"apiVersion": "v1", "kind": "Status", "metadata": {}, "status": "Unknown"}
    )
    with pytest.raises(KubexApiError) as exc_info:
        WatchEvent(Pod, event)
    assert isinstance(exc_info.value.content, str)


def test_watch_event_non_error_type_is_unaffected() -> None:
    event = {
        "type": "ADDED",
        "object": {
            "apiVersion": "v1",
            "kind": "Pod",
            "metadata": {"name": "my-pod", "namespace": "default"},
        },
    }
    watch_event = WatchEvent(Pod, event)
    assert watch_event.type == EventType.ADDED
    assert isinstance(watch_event.object, Pod)
