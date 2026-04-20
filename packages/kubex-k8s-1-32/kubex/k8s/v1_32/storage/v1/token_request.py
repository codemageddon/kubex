from pydantic import Field

from kubex_core.models.base import BaseK8sModel


class TokenRequest(BaseK8sModel):
    """TokenRequest contains parameters of a service account token."""

    audience: str = Field(
        ...,
        alias="audience",
        description='audience is the intended audience of the token in "TokenRequestSpec". It will default to the audiences of kube apiserver.',
    )
    expiration_seconds: int | None = Field(
        default=None,
        alias="expirationSeconds",
        description='expirationSeconds is the duration of validity of the token in "TokenRequestSpec". It has the same default value of "ExpirationSeconds" in "TokenRequestSpec".',
    )
