from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class ParamKind(BaseK8sModel):
    """ParamKind is a tuple of Group Kind and Version."""

    api_version: str | None = Field(
        default=None,
        alias="apiVersion",
        description='APIVersion is the API group version the resources belong to. In format of "group/version". Required.',
    )
    kind: str | None = Field(
        default=None,
        alias="kind",
        description="Kind is the API kind the resources belong to. Required.",
    )
