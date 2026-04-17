from kubex.k8s.v1_35.admissionregistration.v1.expression_warning import (
    ExpressionWarning,
)
from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class TypeChecking(BaseK8sModel):
    """TypeChecking contains results of type checking the expressions in the ValidatingAdmissionPolicy"""

    expression_warnings: list[ExpressionWarning] | None = Field(
        default=None,
        alias="expressionWarnings",
        description="The type checking warnings for each expression.",
    )
