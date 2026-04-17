from __future__ import annotations

from typing import ClassVar, Literal

from kubex.k8s.v1_34.core.v1.local_object_reference import LocalObjectReference
from kubex.k8s.v1_34.core.v1.object_reference import ObjectReference
from kubex_core.models.interfaces import NamespaceScopedEntity
from kubex_core.models.resource_config import ResourceConfig, Scope
from pydantic import Field


class ServiceAccount(NamespaceScopedEntity):
    """ServiceAccount binds together: * a name, understood by users, and perhaps by peripheral systems, for an identity * a principal that can be authenticated and authorized * a set of secrets"""

    __RESOURCE_CONFIG__: ClassVar[ResourceConfig["ServiceAccount"]] = ResourceConfig[
        "ServiceAccount"
    ](
        version="v1",
        kind="ServiceAccount",
        group="core",
        plural="serviceaccounts",
        scope=Scope.NAMESPACE,
    )
    api_version: Literal["v1"] = Field(
        default="v1",
        alias="apiVersion",
        description="APIVersion defines the versioned schema of this representation of an object. Servers should convert recognized schemas to the latest internal value, and may reject unrecognized values. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#resources",
    )
    automount_service_account_token: bool | None = Field(
        default=None,
        alias="automountServiceAccountToken",
        description="AutomountServiceAccountToken indicates whether pods running as this service account should have an API token automatically mounted. Can be overridden at the pod level.",
    )
    image_pull_secrets: list[LocalObjectReference] | None = Field(
        default=None,
        alias="imagePullSecrets",
        description="ImagePullSecrets is a list of references to secrets in the same namespace to use for pulling any images in pods that reference this ServiceAccount. ImagePullSecrets are distinct from Secrets because Secrets can be mounted in the pod, but ImagePullSecrets are only accessed by the kubelet. More info: https://kubernetes.io/docs/concepts/containers/images/#specifying-imagepullsecrets-on-a-pod",
    )
    kind: Literal["ServiceAccount"] = Field(
        default="ServiceAccount",
        alias="kind",
        description="Kind is a string value representing the REST resource this object represents. Servers may infer this from the endpoint the client submits requests to. Cannot be updated. In CamelCase. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds",
    )
    secrets: list[ObjectReference] | None = Field(
        default=None,
        alias="secrets",
        description='Secrets is a list of the secrets in the same namespace that pods running using this ServiceAccount are allowed to use. Pods are only limited to this list if this service account has a "kubernetes.io/enforce-mountable-secrets" annotation set to "true". The "kubernetes.io/enforce-mountable-secrets" annotation is deprecated since v1.32. Prefer separate namespaces to isolate access to mounted secrets. This field should not be used to find auto-generated service account token secrets for use outside of pods. Instead, tokens can be requested directly using the TokenRequest API, or service account token secrets can be manually created. More info: https://kubernetes.io/docs/concepts/configuration/secret',
    )
