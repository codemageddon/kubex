from __future__ import annotations

from typing import ClassVar, Literal

from kubex.k8s.v1_32.admissionregistration.v1beta1.validating_admission_policy_binding_spec import (
    ValidatingAdmissionPolicyBindingSpec,
)
from kubex_core.models.interfaces import ClusterScopedEntity
from kubex_core.models.resource_config import ResourceConfig, Scope
from pydantic import Field


class ValidatingAdmissionPolicyBinding(ClusterScopedEntity):
    """ValidatingAdmissionPolicyBinding binds the ValidatingAdmissionPolicy with paramerized resources. ValidatingAdmissionPolicyBinding and parameter CRDs together define how cluster administrators configure policies for clusters. For a given admission request, each binding will cause its policy to be evaluated N times, where N is 1 for policies/bindings that don't use params, otherwise N is the number of parameters selected by the binding. The CEL expressions of a policy must have a computed CEL cost below the maximum CEL budget. Each evaluation of the policy is given an independent CEL cost budget. Adding/removing policies, bindings, or params can not affect whether a given (policy, binding, param) combination is within its own CEL budget."""

    __RESOURCE_CONFIG__: ClassVar[
        ResourceConfig["ValidatingAdmissionPolicyBinding"]
    ] = ResourceConfig["ValidatingAdmissionPolicyBinding"](
        version="v1beta1",
        kind="ValidatingAdmissionPolicyBinding",
        group="admissionregistration.k8s.io",
        plural="validatingadmissionpolicybindings",
        scope=Scope.CLUSTER,
    )
    api_version: Literal["admissionregistration.k8s.io/v1beta1"] = Field(
        default="admissionregistration.k8s.io/v1beta1",
        alias="apiVersion",
        description="APIVersion defines the versioned schema of this representation of an object. Servers should convert recognized schemas to the latest internal value, and may reject unrecognized values. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#resources",
    )
    kind: Literal["ValidatingAdmissionPolicyBinding"] = Field(
        default="ValidatingAdmissionPolicyBinding",
        alias="kind",
        description="Kind is a string value representing the REST resource this object represents. Servers may infer this from the endpoint the client submits requests to. Cannot be updated. In CamelCase. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds",
    )
    spec: ValidatingAdmissionPolicyBindingSpec | None = Field(
        default=None,
        alias="spec",
        description="Specification of the desired behavior of the ValidatingAdmissionPolicyBinding.",
    )
