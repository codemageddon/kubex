from pydantic import Field

from kubex_core.models.base import BaseK8sModel


class PolicyRule(BaseK8sModel):
    """PolicyRule holds information that describes a policy rule, but does not contain information about who the rule applies to or which namespace the rule applies to."""

    api_groups: list[str] | None = Field(
        default=None,
        alias="apiGroups",
        description='APIGroups is the name of the APIGroup that contains the resources. If multiple API groups are specified, any action requested against one of the enumerated resources in any API group will be allowed. "" represents the core API group and "*" represents all API groups.',
    )
    non_resource_urls: list[str] | None = Field(
        default=None,
        alias="nonResourceURLs",
        description='NonResourceURLs is a set of partial urls that a user should have access to. *s are allowed, but only as the full, final step in the path Since non-resource URLs are not namespaced, this field is only applicable for ClusterRoles referenced from a ClusterRoleBinding. Rules can either apply to API resources (such as "pods" or "secrets") or non-resource URL paths (such as "/api"), but not both.',
    )
    resource_names: list[str] | None = Field(
        default=None,
        alias="resourceNames",
        description="ResourceNames is an optional white list of names that the rule applies to. An empty set means that everything is allowed.",
    )
    resources: list[str] | None = Field(
        default=None,
        alias="resources",
        description="Resources is a list of resources this rule applies to. '*' represents all resources.",
    )
    verbs: list[str] = Field(
        ...,
        alias="verbs",
        description="Verbs is a list of Verbs that apply to ALL the ResourceKinds contained in this rule. '*' represents all verbs.",
    )
