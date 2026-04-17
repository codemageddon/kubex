from __future__ import annotations

from typing import ClassVar, Literal

from kubex.k8s.v1_32.core.v1.pod_template_spec import PodTemplateSpec
from kubex_core.models.interfaces import NamespaceScopedEntity
from kubex_core.models.resource_config import ResourceConfig, Scope
from pydantic import Field


class PodTemplate(NamespaceScopedEntity):
    """PodTemplate describes a template for creating copies of a predefined pod."""

    __RESOURCE_CONFIG__: ClassVar[ResourceConfig["PodTemplate"]] = ResourceConfig[
        "PodTemplate"
    ](
        version="v1",
        kind="PodTemplate",
        group="core",
        plural="podtemplates",
        scope=Scope.NAMESPACE,
    )
    api_version: Literal["v1"] = Field(
        default="v1",
        alias="apiVersion",
        description="APIVersion defines the versioned schema of this representation of an object. Servers should convert recognized schemas to the latest internal value, and may reject unrecognized values. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#resources",
    )
    kind: Literal["PodTemplate"] = Field(
        default="PodTemplate",
        alias="kind",
        description="Kind is a string value representing the REST resource this object represents. Servers may infer this from the endpoint the client submits requests to. Cannot be updated. In CamelCase. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds",
    )
    template: PodTemplateSpec | None = Field(
        default=None,
        alias="template",
        description="Template defines the pods that will be created from this pod template. https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#spec-and-status",
    )
