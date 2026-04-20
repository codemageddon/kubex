from pydantic import Field

from kubex.k8s.v1_37.admissionregistration.v1.type_checking import TypeChecking
from kubex.k8s.v1_37.meta.v1.condition import Condition
from kubex_core.models.base import BaseK8sModel


class ValidatingAdmissionPolicyStatus(BaseK8sModel):
    """ValidatingAdmissionPolicyStatus represents the status of an admission validation policy."""

    conditions: list[Condition] | None = Field(
        default=None,
        alias="conditions",
        description="conditions represent the latest available observations of a policy's current state.",
    )
    observed_generation: int | None = Field(
        default=None,
        alias="observedGeneration",
        description="observedGeneration is the generation observed by the controller.",
    )
    type_checking: TypeChecking | None = Field(
        default=None,
        alias="typeChecking",
        description="typeChecking contains the results of type checking for each expression. Presence of this field indicates the completion of the type checking.",
    )
