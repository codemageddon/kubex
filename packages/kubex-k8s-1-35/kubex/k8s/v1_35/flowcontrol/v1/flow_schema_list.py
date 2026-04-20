from __future__ import annotations

from typing import Literal

from pydantic import Field

from kubex.k8s.v1_35.flowcontrol.v1.flow_schema import FlowSchema
from kubex_core.models.list_entity import ListEntity
from kubex_core.models.metadata import ListMetadata


class FlowSchemaList(ListEntity[FlowSchema]):
    """FlowSchemaList is a list of FlowSchema objects."""

    api_version: Literal["flowcontrol.apiserver.k8s.io/v1"] = Field(
        default="flowcontrol.apiserver.k8s.io/v1",
        alias="apiVersion",
        description="APIVersion defines the versioned schema of this representation of an object. Servers should convert recognized schemas to the latest internal value, and may reject unrecognized values. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#resources",
    )
    items: list[FlowSchema] = Field(
        ..., alias="items", description="`items` is a list of FlowSchemas."
    )
    kind: Literal["FlowSchemaList"] = Field(
        default="FlowSchemaList",
        alias="kind",
        description="Kind is a string value representing the REST resource this object represents. Servers may infer this from the endpoint the client submits requests to. Cannot be updated. In CamelCase. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds",
    )
    metadata: ListMetadata = Field(
        ...,
        alias="metadata",
        description="`metadata` is the standard list metadata. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#metadata",
    )


FlowSchema.__RESOURCE_CONFIG__._list_model = FlowSchemaList
