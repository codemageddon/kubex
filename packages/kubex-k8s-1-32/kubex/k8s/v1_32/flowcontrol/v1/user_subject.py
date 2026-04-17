from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class UserSubject(BaseK8sModel):
    """UserSubject holds detailed information for user-kind subject."""

    name: str = Field(
        ...,
        alias="name",
        description='`name` is the username that matches, or "*" to match all usernames. Required.',
    )
