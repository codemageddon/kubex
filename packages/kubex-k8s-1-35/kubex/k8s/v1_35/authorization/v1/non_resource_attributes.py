from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class NonResourceAttributes(BaseK8sModel):
    """NonResourceAttributes includes the authorization attributes available for non-resource requests to the Authorizer interface"""

    path: str | None = Field(
        default=None, alias="path", description="Path is the URL path of the request"
    )
    verb: str | None = Field(
        default=None, alias="verb", description="Verb is the standard HTTP verb"
    )
