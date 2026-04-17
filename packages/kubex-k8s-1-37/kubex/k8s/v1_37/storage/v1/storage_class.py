from __future__ import annotations

from typing import ClassVar, Literal

from kubex.k8s.v1_37.core.v1.topology_selector_term import TopologySelectorTerm
from kubex_core.models.interfaces import ClusterScopedEntity
from kubex_core.models.resource_config import ResourceConfig, Scope
from pydantic import Field


class StorageClass(ClusterScopedEntity):
    """StorageClass describes the parameters for a class of storage for which PersistentVolumes can be dynamically provisioned. StorageClasses are non-namespaced; the name of the storage class according to etcd is in ObjectMeta.Name."""

    __RESOURCE_CONFIG__: ClassVar[ResourceConfig["StorageClass"]] = ResourceConfig[
        "StorageClass"
    ](
        version="v1",
        kind="StorageClass",
        group="storage.k8s.io",
        plural="storageclasses",
        scope=Scope.CLUSTER,
    )
    allow_volume_expansion: bool | None = Field(
        default=None,
        alias="allowVolumeExpansion",
        description="allowVolumeExpansion shows whether the storage class allow volume expand.",
    )
    allowed_topologies: list[TopologySelectorTerm] | None = Field(
        default=None,
        alias="allowedTopologies",
        description="allowedTopologies restrict the node topologies where volumes can be dynamically provisioned. Each volume plugin defines its own supported topology specifications. An empty TopologySelectorTerm list means there is no topology restriction. This field is only honored by servers that enable the VolumeScheduling feature.",
    )
    api_version: Literal["storage.k8s.io/v1"] = Field(
        default="storage.k8s.io/v1",
        alias="apiVersion",
        description="APIVersion defines the versioned schema of this representation of an object. Servers should convert recognized schemas to the latest internal value, and may reject unrecognized values. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#resources",
    )
    kind: Literal["StorageClass"] = Field(
        default="StorageClass",
        alias="kind",
        description="Kind is a string value representing the REST resource this object represents. Servers may infer this from the endpoint the client submits requests to. Cannot be updated. In CamelCase. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds",
    )
    mount_options: list[str] | None = Field(
        default=None,
        alias="mountOptions",
        description='mountOptions controls the mountOptions for dynamically provisioned PersistentVolumes of this storage class. e.g. ["ro", "soft"]. Not validated - mount of the PVs will simply fail if one is invalid.',
    )
    parameters: dict[str, str] | None = Field(
        default=None,
        alias="parameters",
        description="parameters holds the parameters for the provisioner that should create volumes of this storage class.",
    )
    provisioner: str = Field(
        ...,
        alias="provisioner",
        description="provisioner indicates the type of the provisioner.",
    )
    reclaim_policy: str | None = Field(
        default=None,
        alias="reclaimPolicy",
        description="reclaimPolicy controls the reclaimPolicy for dynamically provisioned PersistentVolumes of this storage class. Defaults to Delete.",
    )
    volume_binding_mode: str | None = Field(
        default=None,
        alias="volumeBindingMode",
        description="volumeBindingMode indicates how PersistentVolumeClaims should be provisioned and bound. When unset, VolumeBindingImmediate is used. This field is only honored by servers that enable the VolumeScheduling feature.",
    )
