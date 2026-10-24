from __future__ import annotations

from typing import ClassVar, Literal

from pydantic import Field

from kubex.k8s.v1_38.core.v1.event_series import EventSeries
from kubex.k8s.v1_38.core.v1.event_source import EventSource
from kubex.k8s.v1_38.core.v1.object_reference import ObjectReference
from kubex_core.models.interfaces import NamespaceScopedEntity
from kubex_core.models.resource_config import ResourceConfig, Scope
from kubex_core.models.types import MicroTime, Time


class Event(NamespaceScopedEntity):
    """Event is a report of an event somewhere in the cluster. Events have a limited retention time and triggers and messages may evolve with time. Event consumers should not rely on the timing of an event with a given Reason reflecting a consistent underlying trigger, or the continued existence of events with that Reason. Events should be treated as informative, best-effort, supplemental data."""

    __RESOURCE_CONFIG__: ClassVar[ResourceConfig["Event"]] = ResourceConfig["Event"](
        version="v1",
        kind="Event",
        group="core",
        plural="events",
        scope=Scope.NAMESPACE,
    )
    action: str | None = Field(
        default=None,
        alias="action",
        description="action is what action was taken/failed regarding to the Regarding object.",
    )
    api_version: Literal["v1"] = Field(
        default="v1",
        alias="apiVersion",
        description="APIVersion defines the versioned schema of this representation of an object. Servers should convert recognized schemas to the latest internal value, and may reject unrecognized values. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#resources",
    )
    count: int | None = Field(
        default=None,
        alias="count",
        description="count is the number of times this event has occurred.",
    )
    event_time: MicroTime | None = Field(
        default=None,
        alias="eventTime",
        description="eventTime is the time when this Event was first observed.",
    )
    first_timestamp: Time | None = Field(
        default=None,
        alias="firstTimestamp",
        description="firstTimestamp is the time at which the event was first recorded. (Time of server receipt is in TypeMeta.)",
    )
    involved_object: ObjectReference = Field(
        ...,
        alias="involvedObject",
        description="involvedObject is the object that this event is about.",
    )
    kind: Literal["Event"] = Field(
        default="Event",
        alias="kind",
        description="Kind is a string value representing the REST resource this object represents. Servers may infer this from the endpoint the client submits requests to. Cannot be updated. In CamelCase. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds",
    )
    last_timestamp: Time | None = Field(
        default=None,
        alias="lastTimestamp",
        description="lastTimestamp is the time at which the most recent occurrence of this event was recorded.",
    )
    message: str | None = Field(
        default=None,
        alias="message",
        description="message is a human-readable description of the status of this operation.",
    )
    reason: str | None = Field(
        default=None,
        alias="reason",
        description="reason is a short, machine understandable string that gives the reason for the transition into the object's current status.",
    )
    related: ObjectReference | None = Field(
        default=None,
        alias="related",
        description="related is an optional secondary object for more complex actions.",
    )
    reporting_component: str | None = Field(
        default=None,
        alias="reportingComponent",
        description="reportingComponent is the name of the controller that emitted this Event, e.g. `kubernetes.io/kubelet`.",
    )
    reporting_instance: str | None = Field(
        default=None,
        alias="reportingInstance",
        description="reportingInstance is the ID of the controller instance, e.g. `kubelet-xyzf`.",
    )
    series: EventSeries | None = Field(
        default=None,
        alias="series",
        description="series is data about the Event series this event represents or nil if it's a singleton Event.",
    )
    source: EventSource | None = Field(
        default=None,
        alias="source",
        description="source is the component reporting this event. Should be a short machine understandable string.",
    )
    type_: str | None = Field(
        default=None,
        alias="type",
        description="type is the type of this event (Normal, Warning), new types could be added in the future",
    )
