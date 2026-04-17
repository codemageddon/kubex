from __future__ import annotations

from typing import Literal

from kubex.k8s.v1_33.policy.v1.pod_disruption_budget import PodDisruptionBudget
from kubex_core.models.list_entity import ListEntity
from kubex_core.models.metadata import ListMetadata
from pydantic import Field


class PodDisruptionBudgetList(ListEntity[PodDisruptionBudget]):
    """PodDisruptionBudgetList is a collection of PodDisruptionBudgets."""

    api_version: Literal["policy/v1"] = Field(
        default="policy/v1",
        alias="apiVersion",
        description="APIVersion defines the versioned schema of this representation of an object. Servers should convert recognized schemas to the latest internal value, and may reject unrecognized values. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#resources",
    )
    items: list[PodDisruptionBudget] = Field(
        ..., alias="items", description="Items is a list of PodDisruptionBudgets"
    )
    kind: Literal["PodDisruptionBudgetList"] = Field(
        default="PodDisruptionBudgetList",
        alias="kind",
        description="Kind is a string value representing the REST resource this object represents. Servers may infer this from the endpoint the client submits requests to. Cannot be updated. In CamelCase. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds",
    )
    metadata: ListMetadata = Field(
        ...,
        alias="metadata",
        description="Standard object's metadata. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#metadata",
    )


PodDisruptionBudget.__RESOURCE_CONFIG__._list_model = PodDisruptionBudgetList
