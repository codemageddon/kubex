from __future__ import annotations

from typing import ClassVar, Literal

from pydantic import Field

from kubex.k8s.v1_32.admissionregistration.v1.validating_webhook import (
    ValidatingWebhook,
)
from kubex_core.models.interfaces import ClusterScopedEntity
from kubex_core.models.resource_config import ResourceConfig, Scope


class ValidatingWebhookConfiguration(ClusterScopedEntity):
    """ValidatingWebhookConfiguration describes the configuration of and admission webhook that accept or reject and object without changing it."""

    __RESOURCE_CONFIG__: ClassVar[ResourceConfig["ValidatingWebhookConfiguration"]] = (
        ResourceConfig["ValidatingWebhookConfiguration"](
            version="v1",
            kind="ValidatingWebhookConfiguration",
            group="admissionregistration.k8s.io",
            plural="validatingwebhookconfigurations",
            scope=Scope.CLUSTER,
        )
    )
    api_version: Literal["admissionregistration.k8s.io/v1"] = Field(
        default="admissionregistration.k8s.io/v1",
        alias="apiVersion",
        description="APIVersion defines the versioned schema of this representation of an object. Servers should convert recognized schemas to the latest internal value, and may reject unrecognized values. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#resources",
    )
    kind: Literal["ValidatingWebhookConfiguration"] = Field(
        default="ValidatingWebhookConfiguration",
        alias="kind",
        description="Kind is a string value representing the REST resource this object represents. Servers may infer this from the endpoint the client submits requests to. Cannot be updated. In CamelCase. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds",
    )
    webhooks: list[ValidatingWebhook] | None = Field(
        default=None,
        alias="webhooks",
        description="Webhooks is a list of webhooks and the affected resources and operations.",
    )
