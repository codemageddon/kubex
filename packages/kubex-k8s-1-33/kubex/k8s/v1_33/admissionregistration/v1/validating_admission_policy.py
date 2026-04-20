from __future__ import annotations

from typing import ClassVar, Literal

from pydantic import Field

from kubex.k8s.v1_33.admissionregistration.v1.validating_admission_policy_spec import (
    ValidatingAdmissionPolicySpec,
)
from kubex.k8s.v1_33.admissionregistration.v1.validating_admission_policy_status import (
    ValidatingAdmissionPolicyStatus,
)
from kubex_core.models.interfaces import ClusterScopedEntity, HasStatusSubresource
from kubex_core.models.resource_config import ResourceConfig, Scope


class ValidatingAdmissionPolicy(ClusterScopedEntity, HasStatusSubresource):
    """ValidatingAdmissionPolicy describes the definition of an admission validation policy that accepts or rejects an object without changing it."""

    __RESOURCE_CONFIG__: ClassVar[ResourceConfig["ValidatingAdmissionPolicy"]] = (
        ResourceConfig["ValidatingAdmissionPolicy"](
            version="v1",
            kind="ValidatingAdmissionPolicy",
            group="admissionregistration.k8s.io",
            plural="validatingadmissionpolicies",
            scope=Scope.CLUSTER,
        )
    )
    api_version: Literal["admissionregistration.k8s.io/v1"] = Field(
        default="admissionregistration.k8s.io/v1",
        alias="apiVersion",
        description="APIVersion defines the versioned schema of this representation of an object. Servers should convert recognized schemas to the latest internal value, and may reject unrecognized values. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#resources",
    )
    kind: Literal["ValidatingAdmissionPolicy"] = Field(
        default="ValidatingAdmissionPolicy",
        alias="kind",
        description="Kind is a string value representing the REST resource this object represents. Servers may infer this from the endpoint the client submits requests to. Cannot be updated. In CamelCase. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds",
    )
    spec: ValidatingAdmissionPolicySpec | None = Field(
        default=None,
        alias="spec",
        description="Specification of the desired behavior of the ValidatingAdmissionPolicy.",
    )
    status: ValidatingAdmissionPolicyStatus | None = Field(
        default=None,
        alias="status",
        description="The status of the ValidatingAdmissionPolicy, including warnings that are useful to determine if the policy behaves in the expected way. Populated by the system. Read-only.",
    )
