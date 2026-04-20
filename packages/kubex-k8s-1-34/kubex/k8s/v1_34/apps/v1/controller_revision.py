from __future__ import annotations

from typing import Any, ClassVar, Literal

from pydantic import Field

from kubex_core.models.interfaces import NamespaceScopedEntity
from kubex_core.models.resource_config import ResourceConfig, Scope


class ControllerRevision(NamespaceScopedEntity):
    """ControllerRevision implements an immutable snapshot of state data. Clients are responsible for serializing and deserializing the objects that contain their internal state. Once a ControllerRevision has been successfully created, it can not be updated. The API Server will fail validation of all requests that attempt to mutate the Data field. ControllerRevisions may, however, be deleted. Note that, due to its use by both the DaemonSet and StatefulSet controllers for update and rollback, this object is beta. However, it may be subject to name and representation changes in future releases, and clients should not depend on its stability. It is primarily for internal use by controllers."""

    __RESOURCE_CONFIG__: ClassVar[ResourceConfig["ControllerRevision"]] = (
        ResourceConfig["ControllerRevision"](
            version="v1",
            kind="ControllerRevision",
            group="apps",
            plural="controllerrevisions",
            scope=Scope.NAMESPACE,
        )
    )
    api_version: Literal["apps/v1"] = Field(
        default="apps/v1",
        alias="apiVersion",
        description="APIVersion defines the versioned schema of this representation of an object. Servers should convert recognized schemas to the latest internal value, and may reject unrecognized values. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#resources",
    )
    data: dict[str, Any] | None = Field(
        default=None,
        alias="data",
        description="Data is the serialized representation of the state.",
    )
    kind: Literal["ControllerRevision"] = Field(
        default="ControllerRevision",
        alias="kind",
        description="Kind is a string value representing the REST resource this object represents. Servers may infer this from the endpoint the client submits requests to. Cannot be updated. In CamelCase. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds",
    )
    revision: int = Field(
        ...,
        alias="revision",
        description="Revision indicates the revision of the state represented by Data.",
    )
