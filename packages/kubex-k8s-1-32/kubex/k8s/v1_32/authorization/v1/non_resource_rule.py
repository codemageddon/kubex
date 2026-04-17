from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class NonResourceRule(BaseK8sModel):
    """NonResourceRule holds information that describes a rule for the non-resource"""

    non_resource_urls: list[str] | None = Field(
        default=None,
        alias="nonResourceURLs",
        description='NonResourceURLs is a set of partial urls that a user should have access to. *s are allowed, but only as the full, final step in the path. "*" means all.',
    )
    verbs: list[str] = Field(
        ...,
        alias="verbs",
        description='Verb is a list of kubernetes non-resource API verbs, like: get, post, put, delete, patch, head, options. "*" means all.',
    )
