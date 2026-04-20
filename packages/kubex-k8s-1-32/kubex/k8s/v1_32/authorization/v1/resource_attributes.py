from pydantic import Field

from kubex.k8s.v1_32.authorization.v1.field_selector_attributes import (
    FieldSelectorAttributes,
)
from kubex.k8s.v1_32.authorization.v1.label_selector_attributes import (
    LabelSelectorAttributes,
)
from kubex_core.models.base import BaseK8sModel


class ResourceAttributes(BaseK8sModel):
    """ResourceAttributes includes the authorization attributes available for resource requests to the Authorizer interface"""

    field_selector: FieldSelectorAttributes | None = Field(
        default=None,
        alias="fieldSelector",
        description="fieldSelector describes the limitation on access based on field. It can only limit access, not broaden it. This field is alpha-level. To use this field, you must enable the `AuthorizeWithSelectors` feature gate (disabled by default).",
    )
    group: str | None = Field(
        default=None,
        alias="group",
        description='Group is the API Group of the Resource. "*" means all.',
    )
    label_selector: LabelSelectorAttributes | None = Field(
        default=None,
        alias="labelSelector",
        description="labelSelector describes the limitation on access based on labels. It can only limit access, not broaden it. This field is alpha-level. To use this field, you must enable the `AuthorizeWithSelectors` feature gate (disabled by default).",
    )
    name: str | None = Field(
        default=None,
        alias="name",
        description='Name is the name of the resource being requested for a "get" or deleted for a "delete". "" (empty) means all.',
    )
    namespace: str | None = Field(
        default=None,
        alias="namespace",
        description='Namespace is the namespace of the action being requested. Currently, there is no distinction between no namespace and all namespaces "" (empty) is defaulted for LocalSubjectAccessReviews "" (empty) is empty for cluster-scoped resources "" (empty) means "all" for namespace scoped resources from a SubjectAccessReview or SelfSubjectAccessReview',
    )
    resource: str | None = Field(
        default=None,
        alias="resource",
        description='Resource is one of the existing resource types. "*" means all.',
    )
    subresource: str | None = Field(
        default=None,
        alias="subresource",
        description='Subresource is one of the existing resource types. "" means none.',
    )
    verb: str | None = Field(
        default=None,
        alias="verb",
        description='Verb is a kubernetes resource API verb, like: get, list, watch, create, update, delete, proxy. "*" means all.',
    )
    version: str | None = Field(
        default=None,
        alias="version",
        description='Version is the API Version of the Resource. "*" means all.',
    )
