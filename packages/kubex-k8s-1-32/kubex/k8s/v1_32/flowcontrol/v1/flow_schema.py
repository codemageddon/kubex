from __future__ import annotations

from typing import ClassVar, Literal

from kubex.k8s.v1_32.flowcontrol.v1.flow_schema_spec import FlowSchemaSpec
from kubex.k8s.v1_32.flowcontrol.v1.flow_schema_status import FlowSchemaStatus
from kubex_core.models.interfaces import ClusterScopedEntity, HasStatusSubresource
from kubex_core.models.resource_config import ResourceConfig, Scope
from pydantic import Field


class FlowSchema(ClusterScopedEntity, HasStatusSubresource):
    """FlowSchema defines the schema of a group of flows. Note that a flow is made up of a set of inbound API requests with similar attributes and is identified by a pair of strings: the name of the FlowSchema and a "flow distinguisher"."""

    __RESOURCE_CONFIG__: ClassVar[ResourceConfig["FlowSchema"]] = ResourceConfig[
        "FlowSchema"
    ](
        version="v1",
        kind="FlowSchema",
        group="flowcontrol.apiserver.k8s.io",
        plural="flowschemas",
        scope=Scope.CLUSTER,
    )
    api_version: Literal["flowcontrol.apiserver.k8s.io/v1"] = Field(
        default="flowcontrol.apiserver.k8s.io/v1",
        alias="apiVersion",
        description="APIVersion defines the versioned schema of this representation of an object. Servers should convert recognized schemas to the latest internal value, and may reject unrecognized values. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#resources",
    )
    kind: Literal["FlowSchema"] = Field(
        default="FlowSchema",
        alias="kind",
        description="Kind is a string value representing the REST resource this object represents. Servers may infer this from the endpoint the client submits requests to. Cannot be updated. In CamelCase. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds",
    )
    spec: FlowSchemaSpec | None = Field(
        default=None,
        alias="spec",
        description="`spec` is the specification of the desired behavior of a FlowSchema. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#spec-and-status",
    )
    status: FlowSchemaStatus | None = Field(
        default=None,
        alias="status",
        description="`status` is the current status of a FlowSchema. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#spec-and-status",
    )
