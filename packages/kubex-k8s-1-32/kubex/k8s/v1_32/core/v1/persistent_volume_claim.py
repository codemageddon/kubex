from __future__ import annotations

from typing import ClassVar, Literal

from kubex.k8s.v1_32.core.v1.persistent_volume_claim_spec import (
    PersistentVolumeClaimSpec,
)
from kubex.k8s.v1_32.core.v1.persistent_volume_claim_status import (
    PersistentVolumeClaimStatus,
)
from kubex_core.models.interfaces import HasStatusSubresource, NamespaceScopedEntity
from kubex_core.models.resource_config import ResourceConfig, Scope
from pydantic import Field


class PersistentVolumeClaim(NamespaceScopedEntity, HasStatusSubresource):
    """PersistentVolumeClaim is a user's request for and claim to a persistent volume"""

    __RESOURCE_CONFIG__: ClassVar[ResourceConfig["PersistentVolumeClaim"]] = (
        ResourceConfig["PersistentVolumeClaim"](
            version="v1",
            kind="PersistentVolumeClaim",
            group="core",
            plural="persistentvolumeclaims",
            scope=Scope.NAMESPACE,
        )
    )
    api_version: Literal["v1"] = Field(
        default="v1",
        alias="apiVersion",
        description="APIVersion defines the versioned schema of this representation of an object. Servers should convert recognized schemas to the latest internal value, and may reject unrecognized values. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#resources",
    )
    kind: Literal["PersistentVolumeClaim"] = Field(
        default="PersistentVolumeClaim",
        alias="kind",
        description="Kind is a string value representing the REST resource this object represents. Servers may infer this from the endpoint the client submits requests to. Cannot be updated. In CamelCase. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds",
    )
    spec: PersistentVolumeClaimSpec | None = Field(
        default=None,
        alias="spec",
        description="spec defines the desired characteristics of a volume requested by a pod author. More info: https://kubernetes.io/docs/concepts/storage/persistent-volumes#persistentvolumeclaims",
    )
    status: PersistentVolumeClaimStatus | None = Field(
        default=None,
        alias="status",
        description="status represents the current information/status of a persistent volume claim. Read-only. More info: https://kubernetes.io/docs/concepts/storage/persistent-volumes#persistentvolumeclaims",
    )
