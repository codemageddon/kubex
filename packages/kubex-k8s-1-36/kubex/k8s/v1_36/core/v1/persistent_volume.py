from __future__ import annotations

from typing import ClassVar, Literal

from pydantic import Field

from kubex.k8s.v1_36.core.v1.persistent_volume_spec import PersistentVolumeSpec
from kubex.k8s.v1_36.core.v1.persistent_volume_status import PersistentVolumeStatus
from kubex_core.models.interfaces import ClusterScopedEntity, HasStatusSubresource
from kubex_core.models.resource_config import ResourceConfig, Scope


class PersistentVolume(ClusterScopedEntity, HasStatusSubresource):
    """PersistentVolume (PV) is a storage resource provisioned by an administrator. It is analogous to a node. More info: https://kubernetes.io/docs/concepts/storage/persistent-volumes"""

    __RESOURCE_CONFIG__: ClassVar[ResourceConfig["PersistentVolume"]] = ResourceConfig[
        "PersistentVolume"
    ](
        version="v1",
        kind="PersistentVolume",
        group="core",
        plural="persistentvolumes",
        scope=Scope.CLUSTER,
    )
    api_version: Literal["v1"] = Field(
        default="v1",
        alias="apiVersion",
        description="APIVersion defines the versioned schema of this representation of an object. Servers should convert recognized schemas to the latest internal value, and may reject unrecognized values. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#resources",
    )
    kind: Literal["PersistentVolume"] = Field(
        default="PersistentVolume",
        alias="kind",
        description="Kind is a string value representing the REST resource this object represents. Servers may infer this from the endpoint the client submits requests to. Cannot be updated. In CamelCase. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds",
    )
    spec: PersistentVolumeSpec | None = Field(
        default=None,
        alias="spec",
        description="spec defines a specification of a persistent volume owned by the cluster. Provisioned by an administrator. More info: https://kubernetes.io/docs/concepts/storage/persistent-volumes#persistent-volumes",
    )
    status: PersistentVolumeStatus | None = Field(
        default=None,
        alias="status",
        description="status represents the current information/status for the persistent volume. Populated by the system. Read-only. More info: https://kubernetes.io/docs/concepts/storage/persistent-volumes#persistent-volumes",
    )
