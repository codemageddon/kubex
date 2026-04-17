from __future__ import annotations

from typing import ClassVar, Literal

from kubex.k8s.v1_30.apps.v1.deployment_spec import DeploymentSpec
from kubex.k8s.v1_30.apps.v1.deployment_status import DeploymentStatus
from kubex_core.models.interfaces import (
    HasScaleSubresource,
    HasStatusSubresource,
    NamespaceScopedEntity,
)
from kubex_core.models.resource_config import ResourceConfig, Scope
from pydantic import Field


class Deployment(NamespaceScopedEntity, HasScaleSubresource, HasStatusSubresource):
    """Deployment enables declarative updates for Pods and ReplicaSets."""

    __RESOURCE_CONFIG__: ClassVar[ResourceConfig["Deployment"]] = ResourceConfig[
        "Deployment"
    ](
        version="v1",
        kind="Deployment",
        group="apps",
        plural="deployments",
        scope=Scope.NAMESPACE,
    )
    api_version: Literal["apps/v1"] = Field(default="apps/v1", alias="apiVersion")
    kind: Literal["Deployment"] = Field(default="Deployment", alias="kind")
    spec: DeploymentSpec = Field(..., alias="spec")
    status: DeploymentStatus | None = Field(default=None, alias="status")
