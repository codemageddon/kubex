from pydantic import Field

from kubex_core.models.base import BaseK8sModel


class TokenReviewSpec(BaseK8sModel):
    """TokenReviewSpec is a description of the token authentication request."""

    audiences: list[str] | None = Field(
        default=None,
        alias="audiences",
        description="audiences is a list of the identifiers that the resource server presented with the token identifies as. Audience-aware token authenticators will verify that the token was intended for at least one of the audiences in this list. If no audiences are provided, the audience will default to the audience of the Kubernetes apiserver.",
    )
    token: str = Field(
        ..., alias="token", description="token is the opaque bearer token."
    )
