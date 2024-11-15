from __future__ import annotations

import json
from enum import Enum
from typing import Any


class VersionMatch(str, Enum):
    EXACT = "Exact"
    NOT_EXACT = "NotOlderThan"


class PropagationPolicy(str, Enum):
    BACKGROUND = "Background"
    FOREGROUND = "Foreground"
    ORPHAN = "Orphan"


class FieldValidation(str, Enum):
    IGNORE = "Ignore"
    STRICT = "Strict"
    WARN = "Warn"


class DryRun(str, Enum):
    ALL = "All"


class Precondition:
    def __init__(
        self,
        resource_version: str | None = None,
        uid: str | None = None,
    ) -> None:
        self.resource_version = resource_version
        self.uid = uid


class ListOptions:
    def __init__(
        self,
        label_selector: str | None = None,
        field_selector: str | None = None,
        timeout: int | None = None,
        limit: int | None = None,
        continue_token: str | None = None,
        version_match: VersionMatch | None = None,
        resource_version: str | None = None,
    ) -> None:
        self.label_selector = label_selector
        self.field_selector = field_selector
        self.timeout = timeout
        self.limit = limit
        self.continue_token = continue_token
        self.version_match = version_match
        self.resource_version = resource_version

    @classmethod
    def default(cls) -> ListOptions:
        return cls()

    def as_query_params(self) -> dict[str, str] | None:
        query_params = {}
        if self.label_selector is not None:
            query_params["labelSelector"] = self.label_selector
        if self.field_selector is not None:
            query_params["fieldSelector"] = self.field_selector
        if self.timeout is not None:
            query_params["timeoutSeconds"] = str(self.timeout)
        if self.limit is not None:
            query_params["limit"] = str(self.limit)
        if self.continue_token is not None:
            query_params["continue"] = self.continue_token
        if self.version_match is not None:
            query_params["resourceVersion"] = self.version_match.value
        if self.resource_version is not None:
            query_params["resourceVersion"] = self.resource_version
        return query_params or None


class WatchOptions:
    def __init__(
        self,
        label_selector: str | None = None,
        field_selector: str | None = None,
        allow_bookmarks: bool | None = None,
        send_initial_events: bool | None = None,
        timeout_seconds: int | None = None,
    ) -> None:
        self.label_selector = label_selector
        self.field_selector = field_selector
        self.allow_bookmarks = allow_bookmarks
        self.send_initial_events = send_initial_events
        self.timeout_seconds = timeout_seconds

    @classmethod
    def default(cls) -> WatchOptions:
        return cls()

    def as_query_params(self) -> dict[str, str]:
        query_params = {"watch": "true"}
        if self.label_selector is not None:
            query_params["labelSelector"] = self.label_selector
        if self.field_selector is not None:
            query_params["fieldSelector"] = self.field_selector
        if self.allow_bookmarks is not None:
            query_params["allowBookmarks"] = "true" if self.allow_bookmarks else "false"
        if self.send_initial_events is not None:
            query_params["sendInitialEvents"] = (
                "true" if self.send_initial_events else "false"
            )
        if self.timeout_seconds is not None:
            query_params["timeoutSeconds"] = str(self.timeout_seconds)
        return query_params


class GetOptions:
    def __init__(
        self,
        resource_version: str | None = None,
    ) -> None:
        self.resource_version = resource_version

    @classmethod
    def default(cls) -> GetOptions:
        return cls()

    def as_query_params(self) -> dict[str, str] | None:
        if self.resource_version is None:
            return None
        return {"resourceVersion": self.resource_version}


def convert_dry_run(dry_run: bool | DryRun | None) -> DryRun | None:
    if dry_run is None:
        return None
    if isinstance(dry_run, DryRun):
        return dry_run
    return DryRun.ALL if dry_run else None


class PostOptions:
    def __init__(
        self,
        dry_run: bool | DryRun | None = None,
        field_manager: str | None = None,
    ) -> None:
        self.dry_run = dry_run
        self.field_manager = field_manager

    @classmethod
    def default(cls) -> PostOptions:
        return cls()

    def as_query_params(self) -> dict[str, str] | None:
        query_params = {}
        dry_run = convert_dry_run(self.dry_run)
        if dry_run is not None:
            query_params["dryRun"] = dry_run.value
        if self.field_manager is not None:
            query_params["fieldManager"] = self.field_manager
        return query_params or None


class PatchOptions:
    def __init__(
        self,
        dry_run: bool | DryRun | None = None,
        field_manager: str | None = None,
        force: bool | None = None,
        field_validation: FieldValidation | None = None,
    ) -> None:
        self.dry_run = dry_run
        self.field_manager = field_manager
        self.force = force
        self.field_validation = field_validation

    @classmethod
    def default(cls) -> PatchOptions:
        return cls()

    def as_query_params(self) -> dict[str, str] | None:
        query_params = {}
        dry_run = convert_dry_run(self.dry_run)
        if dry_run is not None:
            query_params["dryRun"] = dry_run.value
        if self.field_manager is not None:
            query_params["fieldManager"] = self.field_manager
        if self.force is not None:
            query_params["force"] = "true" if self.force else "false"
        if self.field_validation is not None:
            query_params["fieldValidation"] = self.field_validation.value
        return query_params or None


class DeleteOptions:
    def __init__(
        self,
        dry_run: bool | DryRun | None = None,
        grace_period_seconds: int | None = None,
        propagation_policy: PropagationPolicy | None = None,
        preconditions: Precondition | None = None,
    ) -> None:
        self.dry_run = dry_run
        self.grace_period_seconds = grace_period_seconds
        self.propagation_policy = propagation_policy
        self.preconditions = preconditions

    @classmethod
    def default(cls) -> DeleteOptions:
        return cls()

    def as_request_body(self) -> str | None:
        body: dict[str, Any] = {}
        dry_run = convert_dry_run(self.dry_run)
        if dry_run is not None:
            body["dryRun"] = dry_run.value
        if self.grace_period_seconds is not None:
            body["gracePeriodSeconds"] = str(self.grace_period_seconds)
        if self.propagation_policy is not None:
            body["propagationPolicy"] = self.propagation_policy.value
        if self.preconditions is not None:
            if self.preconditions.resource_version is not None:
                body["preconditions"] = {
                    "resourceVersion": self.preconditions.resource_version
                }
            if self.preconditions.uid is not None:
                body["preconditions"] = {"uid": self.preconditions.uid}
        if body:
            return json.dumps(body)
        return None


class LogOptions:
    def __init__(
        self,
        container: str | None = None,
        limit_bytes: int | None = None,
        pretty: bool | None = None,
        previous: bool | None = None,
        since_seconds: int | None = None,
        tail_lines: int | None = None,
        timestamps: bool | None = None,
    ) -> None:
        self.container = container
        self.limit_bytes = limit_bytes
        self.pretty = pretty
        self.previous = previous
        self.since_seconds = since_seconds
        self.tail_lines = tail_lines
        self.timestamps = timestamps

    @classmethod
    def default(cls) -> LogOptions:
        return cls()

    def as_query_params(self) -> dict[str, str] | None:
        result: dict[str, str] = {}
        if self.container is not None:
            result["container"] = self.container
        if self.limit_bytes is not None:
            result["limitBytes"] = str(self.limit_bytes)
        if self.pretty is not None:
            result["pretty"] = "true" if self.pretty else "false"
        if self.previous is not None:
            result["previous"] = "true" if self.previous else "false"
        if self.since_seconds is not None:
            result["sinceSeconds"] = str(self.since_seconds)
        if self.tail_lines is not None:
            result["tailLines"] = str(self.tail_lines)
        if self.timestamps is not None:
            result["timestamps"] = "true" if self.timestamps else "false"
        return result or None
