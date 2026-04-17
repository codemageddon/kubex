from __future__ import annotations

from typing import ClassVar, Literal

from kubex.k8s.v1_36.apps.v1.deployment_spec import DeploymentSpec
from kubex.k8s.v1_36.apps.v1.deployment_status import DeploymentStatus
from kubex_core.models.interfaces import ClusterScopedEntity, HasStatusSubresource
from kubex_core.models.resource_config import ResourceConfig, Scope
from pydantic import Field


class Deployment(ClusterScopedEntity, HasStatusSubresource):
    """Deployment enables declarative updates for Pods and ReplicaSets."""

    __RESOURCE_CONFIG__: ClassVar[ResourceConfig["Deployment"]] = ResourceConfig[
        "Deployment"
    ](
        version="v1",
        kind="Deployment",
        group="apps",
        plural="deployments",
        scope=Scope.CLUSTER,
    )
    api_version: Literal["apps/v1"] = Field(
        default="apps/v1",
        alias="apiVersion",
        description="APIVersion defines the versioned schema of this representation of an object. Servers should convert recognized schemas to the latest internal value, and may reject unrecognized values. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#resources",
    )
    kind: Literal["Deployment"] = Field(
        default="Deployment",
        alias="kind",
        description="Kind is a string value representing the REST resource this object represents. Servers may infer this from the endpoint the client submits requests to. Cannot be updated. In CamelCase. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds",
    )
    spec: DeploymentSpec | None = Field(
        default=None,
        alias="spec",
        description="Specification of the desired behavior of the Deployment.",
    )
    status: DeploymentStatus | None = Field(
        default=None,
        alias="status",
        description="Most recently observed status of the Deployment.",
    )
