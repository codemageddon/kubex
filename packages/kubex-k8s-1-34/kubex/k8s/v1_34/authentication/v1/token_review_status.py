from pydantic import Field

from kubex.k8s.v1_34.authentication.v1.user_info import UserInfo
from kubex_core.models.base import BaseK8sModel


class TokenReviewStatus(BaseK8sModel):
    """TokenReviewStatus is the result of the token authentication request."""

    audiences: list[str] | None = Field(
        default=None,
        alias="audiences",
        description='Audiences are audience identifiers chosen by the authenticator that are compatible with both the TokenReview and token. An identifier is any identifier in the intersection of the TokenReviewSpec audiences and the token\'s audiences. A client of the TokenReview API that sets the spec.audiences field should validate that a compatible audience identifier is returned in the status.audiences field to ensure that the TokenReview server is audience aware. If a TokenReview returns an empty status.audience field where status.authenticated is "true", the token is valid against the audience of the Kubernetes API server.',
    )
    authenticated: bool | None = Field(
        default=None,
        alias="authenticated",
        description="Authenticated indicates that the token was associated with a known user.",
    )
    error: str | None = Field(
        default=None,
        alias="error",
        description="Error indicates that the token couldn't be checked",
    )
    user: UserInfo | None = Field(
        default=None,
        alias="user",
        description="User is the UserInfo associated with the provided token.",
    )
