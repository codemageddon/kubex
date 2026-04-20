from pydantic import Field

from kubex_core.models.base import BaseK8sModel


class ExternalDocumentation(BaseK8sModel):
    """ExternalDocumentation allows referencing an external resource for extended documentation."""

    description: str | None = Field(default=None, alias="description")
    url: str | None = Field(default=None, alias="url")
