from __future__ import annotations

from typing import Literal

from kubex.k8s.v1_30.apps.v1.deployment import Deployment
from kubex_core.models.list_entity import ListEntity
from kubex_core.models.metadata import ListMetadata
from pydantic import Field


class DeploymentList(ListEntity[Deployment]):
    """DeploymentList is a list of Deployments."""

    api_version: Literal["apps/v1"] = Field(default="apps/v1", alias="apiVersion")
    items: list[Deployment] = Field(..., alias="items")
    kind: Literal["DeploymentList"] = Field(default="DeploymentList", alias="kind")
    metadata: ListMetadata = Field(..., alias="metadata")


Deployment.__RESOURCE_CONFIG__._list_model = DeploymentList
