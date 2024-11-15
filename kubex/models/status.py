from typing import Literal

from .base import BaseK8sModel
from .base_entity import BaseEntity
from .resource_config import ResourceConfig, Scope


class StatusCause(BaseK8sModel):
    """StatusCause provides more information about an api.Status failure, including cases when multiple errors are encountered."""

    message: str
    """A human-readable description of the cause of the error. This field may be presented as-is to a reader."""
    field: str | None = None
    """The field of the resource that has caused this error, as named by its JSON serialization. May include dot and postfix notation for nested attributes. Arrays are zero-indexed. Fields may appear more than once in an array of causes due to fields having multiple errors. Optional. Examples: "name" - the field "name" on the current resource "items[0].name" - the field "name" on the first array entry in \"items\"
    """
    reason: str | None = None
    """A machine-readable description of the cause of the error. If this value is empty there is no information available."""


class StatusDetails(BaseK8sModel):
    """tatusDetails is a set of additional properties that MAY be set by the server to provide additional information about a response. The Reason field of a Status object defines what attributes will be set. Clients must ignore fields that do not match the defined type of each attribute, and should assume that any attribute may be empty, invalid, or under defined."""

    causes: list[StatusCause] | None = None
    """The Causes array includes more details associated with the StatusReason failure. Not all StatusReasons may provide detailed causes."""
    name: str | None = None
    """The name attribute of the resource associated with the status StatusReason (when there is a single name which can be described)."""
    group: str | None = None
    """The group attribute of the resource associated with the status StatusReason."""
    kind: str | None = None
    """The kind attribute of the resource associated with the status StatusReason. On some operations may differ from the requested resource Kind. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds"""
    retry_after_seconds: int | None = None
    """If specified, the time in seconds before the operation should be retried. Some errors may indicate the client must take an alternate action - for those errors this field may indicate how long to wait before taking the alternate action."""
    uid: str | None = None
    """UID of the resource. (when there is a single resource which can be described). More info: http://kubernetes.io/docs/user-guide/identifiers#uids"""


class Status(BaseEntity):
    """Status is a return value for calls that don't return other objects."""

    api_version: Literal["meta/v1"] | None = "meta/v1"
    """APIVersion defines the versioned schema of this representation of an object. Servers should convert recognized schemas to the latest internal value, and may reject unrecognized values. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#resources"""
    kind: Literal["Status"] | None = "Status"
    """Kind is a string value representing the REST resource this object represents. Servers may infer this from the endpoint the client submits requests to. Cannot be updated. In CamelCase. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds"""
    code: int = 0
    """Suggested HTTP return code for this status, 0 if not set."""
    details: StatusDetails | None = None
    """Extended data associated with the reason. Each reason may define its own extended details. This field is optional and the data returned is not guaranteed to conform to any schema except that defined by the reason type."""
    message: str | None = None
    """A human-readable description of the status of this operation."""
    reason: str | None = None
    """A machine-readable description of why this operation is in the "Failure" status. If this value is empty there is no information available. A Reason clarifies an HTTP status code but does not override it."""
    status: Literal["Success", "Failure"]
    """Status of the operation. One of: "Success" or "Failure". More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#spec-and-status"""

    __RESOURCE_CONFIG__ = ResourceConfig["Status"](
        version="meta/v1",
        kind="Status",
        plural="statuses",
        scope=Scope.CLUSTER,
    )
