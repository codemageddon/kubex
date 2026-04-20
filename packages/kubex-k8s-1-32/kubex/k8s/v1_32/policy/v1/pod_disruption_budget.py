from __future__ import annotations

from typing import ClassVar, Literal

from pydantic import Field

from kubex.k8s.v1_32.policy.v1.pod_disruption_budget_spec import PodDisruptionBudgetSpec
from kubex.k8s.v1_32.policy.v1.pod_disruption_budget_status import (
    PodDisruptionBudgetStatus,
)
from kubex_core.models.interfaces import HasStatusSubresource, NamespaceScopedEntity
from kubex_core.models.resource_config import ResourceConfig, Scope


class PodDisruptionBudget(NamespaceScopedEntity, HasStatusSubresource):
    """PodDisruptionBudget is an object to define the max disruption that can be caused to a collection of pods"""

    __RESOURCE_CONFIG__: ClassVar[ResourceConfig["PodDisruptionBudget"]] = (
        ResourceConfig["PodDisruptionBudget"](
            version="v1",
            kind="PodDisruptionBudget",
            group="policy",
            plural="poddisruptionbudgets",
            scope=Scope.NAMESPACE,
        )
    )
    api_version: Literal["policy/v1"] = Field(
        default="policy/v1",
        alias="apiVersion",
        description="APIVersion defines the versioned schema of this representation of an object. Servers should convert recognized schemas to the latest internal value, and may reject unrecognized values. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#resources",
    )
    kind: Literal["PodDisruptionBudget"] = Field(
        default="PodDisruptionBudget",
        alias="kind",
        description="Kind is a string value representing the REST resource this object represents. Servers may infer this from the endpoint the client submits requests to. Cannot be updated. In CamelCase. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds",
    )
    spec: PodDisruptionBudgetSpec | None = Field(
        default=None,
        alias="spec",
        description="Specification of the desired behavior of the PodDisruptionBudget.",
    )
    status: PodDisruptionBudgetStatus | None = Field(
        default=None,
        alias="status",
        description="Most recently observed status of the PodDisruptionBudget.",
    )
