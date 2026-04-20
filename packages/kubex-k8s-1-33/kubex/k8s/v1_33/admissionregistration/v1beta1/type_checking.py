from pydantic import Field

from kubex.k8s.v1_33.admissionregistration.v1beta1.expression_warning import (
    ExpressionWarning,
)
from kubex_core.models.base import BaseK8sModel


class TypeChecking(BaseK8sModel):
    """TypeChecking contains results of type checking the expressions in the ValidatingAdmissionPolicy"""

    expression_warnings: list[ExpressionWarning] | None = Field(
        default=None,
        alias="expressionWarnings",
        description="The type checking warnings for each expression.",
    )
