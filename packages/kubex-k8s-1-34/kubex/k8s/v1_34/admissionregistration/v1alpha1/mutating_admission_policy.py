from __future__ import annotations

from typing import ClassVar, Literal

from kubex.k8s.v1_34.admissionregistration.v1alpha1.mutating_admission_policy_spec import (
    MutatingAdmissionPolicySpec,
)
from kubex_core.models.interfaces import ClusterScopedEntity
from kubex_core.models.resource_config import ResourceConfig, Scope
from pydantic import Field


class MutatingAdmissionPolicy(ClusterScopedEntity):
    """MutatingAdmissionPolicy describes the definition of an admission mutation policy that mutates the object coming into admission chain."""

    __RESOURCE_CONFIG__: ClassVar[ResourceConfig["MutatingAdmissionPolicy"]] = (
        ResourceConfig["MutatingAdmissionPolicy"](
            version="v1alpha1",
            kind="MutatingAdmissionPolicy",
            group="admissionregistration.k8s.io",
            plural="mutatingadmissionpolicies",
            scope=Scope.CLUSTER,
        )
    )
    api_version: Literal["admissionregistration.k8s.io/v1alpha1"] = Field(
        default="admissionregistration.k8s.io/v1alpha1",
        alias="apiVersion",
        description="APIVersion defines the versioned schema of this representation of an object. Servers should convert recognized schemas to the latest internal value, and may reject unrecognized values. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#resources",
    )
    kind: Literal["MutatingAdmissionPolicy"] = Field(
        default="MutatingAdmissionPolicy",
        alias="kind",
        description="Kind is a string value representing the REST resource this object represents. Servers may infer this from the endpoint the client submits requests to. Cannot be updated. In CamelCase. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds",
    )
    spec: MutatingAdmissionPolicySpec | None = Field(
        default=None,
        alias="spec",
        description="Specification of the desired behavior of the MutatingAdmissionPolicy.",
    )
