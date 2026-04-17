from __future__ import annotations

from typing import ClassVar, Literal

from kubex.k8s.v1_33.admissionregistration.v1alpha1.mutating_admission_policy_binding_spec import (
    MutatingAdmissionPolicyBindingSpec,
)
from kubex_core.models.interfaces import ClusterScopedEntity
from kubex_core.models.resource_config import ResourceConfig, Scope
from pydantic import Field


class MutatingAdmissionPolicyBinding(ClusterScopedEntity):
    """MutatingAdmissionPolicyBinding binds the MutatingAdmissionPolicy with parametrized resources. MutatingAdmissionPolicyBinding and the optional parameter resource together define how cluster administrators configure policies for clusters. For a given admission request, each binding will cause its policy to be evaluated N times, where N is 1 for policies/bindings that don't use params, otherwise N is the number of parameters selected by the binding. Each evaluation is constrained by a [runtime cost budget](https://kubernetes.io/docs/reference/using-api/cel/#runtime-cost-budget). Adding/removing policies, bindings, or params can not affect whether a given (policy, binding, param) combination is within its own CEL budget."""

    __RESOURCE_CONFIG__: ClassVar[ResourceConfig["MutatingAdmissionPolicyBinding"]] = (
        ResourceConfig["MutatingAdmissionPolicyBinding"](
            version="v1alpha1",
            kind="MutatingAdmissionPolicyBinding",
            group="admissionregistration.k8s.io",
            plural="mutatingadmissionpolicybindings",
            scope=Scope.CLUSTER,
        )
    )
    api_version: Literal["admissionregistration.k8s.io/v1alpha1"] = Field(
        default="admissionregistration.k8s.io/v1alpha1",
        alias="apiVersion",
        description="APIVersion defines the versioned schema of this representation of an object. Servers should convert recognized schemas to the latest internal value, and may reject unrecognized values. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#resources",
    )
    kind: Literal["MutatingAdmissionPolicyBinding"] = Field(
        default="MutatingAdmissionPolicyBinding",
        alias="kind",
        description="Kind is a string value representing the REST resource this object represents. Servers may infer this from the endpoint the client submits requests to. Cannot be updated. In CamelCase. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds",
    )
    spec: MutatingAdmissionPolicyBindingSpec | None = Field(
        default=None,
        alias="spec",
        description="Specification of the desired behavior of the MutatingAdmissionPolicyBinding.",
    )
