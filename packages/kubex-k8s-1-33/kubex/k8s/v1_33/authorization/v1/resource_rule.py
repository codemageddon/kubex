from pydantic import Field

from kubex_core.models.base import BaseK8sModel


class ResourceRule(BaseK8sModel):
    """ResourceRule is the list of actions the subject is allowed to perform on resources. The list ordering isn't significant, may contain duplicates, and possibly be incomplete."""

    api_groups: list[str] | None = Field(
        default=None,
        alias="apiGroups",
        description='APIGroups is the name of the APIGroup that contains the resources. If multiple API groups are specified, any action requested against one of the enumerated resources in any API group will be allowed. "*" means all.',
    )
    resource_names: list[str] | None = Field(
        default=None,
        alias="resourceNames",
        description='ResourceNames is an optional white list of names that the rule applies to. An empty set means that everything is allowed. "*" means all.',
    )
    resources: list[str] | None = Field(
        default=None,
        alias="resources",
        description='Resources is a list of resources this rule applies to. "*" means all in the specified apiGroups. "*/foo" represents the subresource \'foo\' for all resources in the specified apiGroups.',
    )
    verbs: list[str] = Field(
        ...,
        alias="verbs",
        description='Verb is a list of kubernetes resource API verbs, like: get, list, watch, create, update, delete, proxy. "*" means all.',
    )
