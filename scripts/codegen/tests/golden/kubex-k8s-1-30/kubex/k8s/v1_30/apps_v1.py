from enum import Enum
from typing import ClassVar, Literal

from kubex.k8s.v1_30._common import IntOrString
from kubex_core.models.base import BaseK8sModel
from kubex_core.models.interfaces import (
    HasScaleSubresource,
    HasStatusSubresource,
    NamespaceScopedEntity,
)
from kubex_core.models.list_entity import ListEntity
from kubex_core.models.metadata import ListMetadata
from kubex_core.models.resource_config import ResourceConfig, Scope
from pydantic import Field


class DeploymentConditionType(str, Enum):
    AVAILABLE = "Available"
    PROGRESSING = "Progressing"
    REPLICA_FAILURE = "ReplicaFailure"


class DeploymentCondition(BaseK8sModel):
    """DeploymentCondition describes a condition of a Deployment."""

    reason: str | None = Field(default=None, alias="reason")
    status: str = Field(..., alias="status")
    type_: DeploymentConditionType = Field(
        ..., alias="type", description="Type of deployment condition."
    )


class DeploymentSpec(BaseK8sModel):
    """DeploymentSpec is the specification of the desired behavior of the Deployment."""

    max_surge: IntOrString | None = Field(default=None, alias="maxSurge")
    min_ready_seconds: int | None = Field(default=None, alias="minReadySeconds")
    paused: bool | None = Field(default=None, alias="paused")
    replicas: int | None = Field(default=None, alias="replicas")


class DeploymentStatus(BaseK8sModel):
    """DeploymentStatus is the most recently observed status of the Deployment."""

    available_replicas: int | None = Field(default=None, alias="availableReplicas")
    conditions: list[DeploymentCondition] | None = Field(
        default=None, alias="conditions"
    )
    replicas: int | None = Field(default=None, alias="replicas")


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


class DeploymentList(ListEntity[Deployment]):
    """DeploymentList is a list of Deployments."""

    api_version: Literal["apps/v1"] = Field(default="apps/v1", alias="apiVersion")
    items: list[Deployment] = Field(..., alias="items")
    kind: Literal["DeploymentList"] = Field(default="DeploymentList", alias="kind")
    metadata: ListMetadata = Field(..., alias="metadata")


Deployment.__RESOURCE_CONFIG__._list_model = DeploymentList
