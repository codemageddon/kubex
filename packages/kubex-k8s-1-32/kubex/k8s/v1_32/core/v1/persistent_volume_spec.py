from kubex.k8s.v1_32.core.v1.aws_elastic_block_store_volume_source import (
    AWSElasticBlockStoreVolumeSource,
)
from kubex.k8s.v1_32.core.v1.azure_disk_volume_source import AzureDiskVolumeSource
from kubex.k8s.v1_32.core.v1.azure_file_persistent_volume_source import (
    AzureFilePersistentVolumeSource,
)
from kubex.k8s.v1_32.core.v1.ceph_fs_persistent_volume_source import (
    CephFSPersistentVolumeSource,
)
from kubex.k8s.v1_32.core.v1.cinder_persistent_volume_source import (
    CinderPersistentVolumeSource,
)
from kubex.k8s.v1_32.core.v1.csi_persistent_volume_source import (
    CSIPersistentVolumeSource,
)
from kubex.k8s.v1_32.core.v1.fc_volume_source import FCVolumeSource
from kubex.k8s.v1_32.core.v1.flex_persistent_volume_source import (
    FlexPersistentVolumeSource,
)
from kubex.k8s.v1_32.core.v1.flocker_volume_source import FlockerVolumeSource
from kubex.k8s.v1_32.core.v1.gce_persistent_disk_volume_source import (
    GCEPersistentDiskVolumeSource,
)
from kubex.k8s.v1_32.core.v1.glusterfs_persistent_volume_source import (
    GlusterfsPersistentVolumeSource,
)
from kubex.k8s.v1_32.core.v1.host_path_volume_source import HostPathVolumeSource
from kubex.k8s.v1_32.core.v1.iscsi_persistent_volume_source import (
    ISCSIPersistentVolumeSource,
)
from kubex.k8s.v1_32.core.v1.local_volume_source import LocalVolumeSource
from kubex.k8s.v1_32.core.v1.nfs_volume_source import NFSVolumeSource
from kubex.k8s.v1_32.core.v1.object_reference import ObjectReference
from kubex.k8s.v1_32.core.v1.photon_persistent_disk_volume_source import (
    PhotonPersistentDiskVolumeSource,
)
from kubex.k8s.v1_32.core.v1.portworx_volume_source import PortworxVolumeSource
from kubex.k8s.v1_32.core.v1.quobyte_volume_source import QuobyteVolumeSource
from kubex.k8s.v1_32.core.v1.rbd_persistent_volume_source import (
    RBDPersistentVolumeSource,
)
from kubex.k8s.v1_32.core.v1.scale_io_persistent_volume_source import (
    ScaleIOPersistentVolumeSource,
)
from kubex.k8s.v1_32.core.v1.storage_os_persistent_volume_source import (
    StorageOSPersistentVolumeSource,
)
from kubex.k8s.v1_32.core.v1.volume_node_affinity import VolumeNodeAffinity
from kubex.k8s.v1_32.core.v1.vsphere_virtual_disk_volume_source import (
    VsphereVirtualDiskVolumeSource,
)
from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class PersistentVolumeSpec(BaseK8sModel):
    """PersistentVolumeSpec is the specification of a persistent volume."""

    access_modes: list[str] | None = Field(
        default=None,
        alias="accessModes",
        description="accessModes contains all ways the volume can be mounted. More info: https://kubernetes.io/docs/concepts/storage/persistent-volumes#access-modes",
    )
    aws_elastic_block_store: AWSElasticBlockStoreVolumeSource | None = Field(
        default=None,
        alias="awsElasticBlockStore",
        description="awsElasticBlockStore represents an AWS Disk resource that is attached to a kubelet's host machine and then exposed to the pod. Deprecated: AWSElasticBlockStore is deprecated. All operations for the in-tree awsElasticBlockStore type are redirected to the ebs.csi.aws.com CSI driver. More info: https://kubernetes.io/docs/concepts/storage/volumes#awselasticblockstore",
    )
    azure_disk: AzureDiskVolumeSource | None = Field(
        default=None,
        alias="azureDisk",
        description="azureDisk represents an Azure Data Disk mount on the host and bind mount to the pod. Deprecated: AzureDisk is deprecated. All operations for the in-tree azureDisk type are redirected to the disk.csi.azure.com CSI driver.",
    )
    azure_file: AzureFilePersistentVolumeSource | None = Field(
        default=None,
        alias="azureFile",
        description="azureFile represents an Azure File Service mount on the host and bind mount to the pod. Deprecated: AzureFile is deprecated. All operations for the in-tree azureFile type are redirected to the file.csi.azure.com CSI driver.",
    )
    capacity: dict[str, str] | None = Field(
        default=None,
        alias="capacity",
        description="capacity is the description of the persistent volume's resources and capacity. More info: https://kubernetes.io/docs/concepts/storage/persistent-volumes#capacity",
    )
    cephfs: CephFSPersistentVolumeSource | None = Field(
        default=None,
        alias="cephfs",
        description="cephFS represents a Ceph FS mount on the host that shares a pod's lifetime. Deprecated: CephFS is deprecated and the in-tree cephfs type is no longer supported.",
    )
    cinder: CinderPersistentVolumeSource | None = Field(
        default=None,
        alias="cinder",
        description="cinder represents a cinder volume attached and mounted on kubelets host machine. Deprecated: Cinder is deprecated. All operations for the in-tree cinder type are redirected to the cinder.csi.openstack.org CSI driver. More info: https://examples.k8s.io/mysql-cinder-pd/README.md",
    )
    claim_ref: ObjectReference | None = Field(
        default=None,
        alias="claimRef",
        description="claimRef is part of a bi-directional binding between PersistentVolume and PersistentVolumeClaim. Expected to be non-nil when bound. claim.VolumeName is the authoritative bind between PV and PVC. More info: https://kubernetes.io/docs/concepts/storage/persistent-volumes#binding",
    )
    csi: CSIPersistentVolumeSource | None = Field(
        default=None,
        alias="csi",
        description="csi represents storage that is handled by an external CSI driver.",
    )
    fc: FCVolumeSource | None = Field(
        default=None,
        alias="fc",
        description="fc represents a Fibre Channel resource that is attached to a kubelet's host machine and then exposed to the pod.",
    )
    flex_volume: FlexPersistentVolumeSource | None = Field(
        default=None,
        alias="flexVolume",
        description="flexVolume represents a generic volume resource that is provisioned/attached using an exec based plugin. Deprecated: FlexVolume is deprecated. Consider using a CSIDriver instead.",
    )
    flocker: FlockerVolumeSource | None = Field(
        default=None,
        alias="flocker",
        description="flocker represents a Flocker volume attached to a kubelet's host machine and exposed to the pod for its usage. This depends on the Flocker control service being running. Deprecated: Flocker is deprecated and the in-tree flocker type is no longer supported.",
    )
    gce_persistent_disk: GCEPersistentDiskVolumeSource | None = Field(
        default=None,
        alias="gcePersistentDisk",
        description="gcePersistentDisk represents a GCE Disk resource that is attached to a kubelet's host machine and then exposed to the pod. Provisioned by an admin. Deprecated: GCEPersistentDisk is deprecated. All operations for the in-tree gcePersistentDisk type are redirected to the pd.csi.storage.gke.io CSI driver. More info: https://kubernetes.io/docs/concepts/storage/volumes#gcepersistentdisk",
    )
    glusterfs: GlusterfsPersistentVolumeSource | None = Field(
        default=None,
        alias="glusterfs",
        description="glusterfs represents a Glusterfs volume that is attached to a host and exposed to the pod. Provisioned by an admin. Deprecated: Glusterfs is deprecated and the in-tree glusterfs type is no longer supported. More info: https://examples.k8s.io/volumes/glusterfs/README.md",
    )
    host_path: HostPathVolumeSource | None = Field(
        default=None,
        alias="hostPath",
        description="hostPath represents a directory on the host. Provisioned by a developer or tester. This is useful for single-node development and testing only! On-host storage is not supported in any way and WILL NOT WORK in a multi-node cluster. More info: https://kubernetes.io/docs/concepts/storage/volumes#hostpath",
    )
    iscsi: ISCSIPersistentVolumeSource | None = Field(
        default=None,
        alias="iscsi",
        description="iscsi represents an ISCSI Disk resource that is attached to a kubelet's host machine and then exposed to the pod. Provisioned by an admin.",
    )
    local: LocalVolumeSource | None = Field(
        default=None,
        alias="local",
        description="local represents directly-attached storage with node affinity",
    )
    mount_options: list[str] | None = Field(
        default=None,
        alias="mountOptions",
        description='mountOptions is the list of mount options, e.g. ["ro", "soft"]. Not validated - mount will simply fail if one is invalid. More info: https://kubernetes.io/docs/concepts/storage/persistent-volumes/#mount-options',
    )
    nfs: NFSVolumeSource | None = Field(
        default=None,
        alias="nfs",
        description="nfs represents an NFS mount on the host. Provisioned by an admin. More info: https://kubernetes.io/docs/concepts/storage/volumes#nfs",
    )
    node_affinity: VolumeNodeAffinity | None = Field(
        default=None,
        alias="nodeAffinity",
        description="nodeAffinity defines constraints that limit what nodes this volume can be accessed from. This field influences the scheduling of pods that use this volume.",
    )
    persistent_volume_reclaim_policy: str | None = Field(
        default=None,
        alias="persistentVolumeReclaimPolicy",
        description="persistentVolumeReclaimPolicy defines what happens to a persistent volume when released from its claim. Valid options are Retain (default for manually created PersistentVolumes), Delete (default for dynamically provisioned PersistentVolumes), and Recycle (deprecated). Recycle must be supported by the volume plugin underlying this PersistentVolume. More info: https://kubernetes.io/docs/concepts/storage/persistent-volumes#reclaiming",
    )
    photon_persistent_disk: PhotonPersistentDiskVolumeSource | None = Field(
        default=None,
        alias="photonPersistentDisk",
        description="photonPersistentDisk represents a PhotonController persistent disk attached and mounted on kubelets host machine. Deprecated: PhotonPersistentDisk is deprecated and the in-tree photonPersistentDisk type is no longer supported.",
    )
    portworx_volume: PortworxVolumeSource | None = Field(
        default=None,
        alias="portworxVolume",
        description="portworxVolume represents a portworx volume attached and mounted on kubelets host machine. Deprecated: PortworxVolume is deprecated. All operations for the in-tree portworxVolume type are redirected to the pxd.portworx.com CSI driver when the CSIMigrationPortworx feature-gate is on.",
    )
    quobyte: QuobyteVolumeSource | None = Field(
        default=None,
        alias="quobyte",
        description="quobyte represents a Quobyte mount on the host that shares a pod's lifetime. Deprecated: Quobyte is deprecated and the in-tree quobyte type is no longer supported.",
    )
    rbd: RBDPersistentVolumeSource | None = Field(
        default=None,
        alias="rbd",
        description="rbd represents a Rados Block Device mount on the host that shares a pod's lifetime. Deprecated: RBD is deprecated and the in-tree rbd type is no longer supported. More info: https://examples.k8s.io/volumes/rbd/README.md",
    )
    scale_io: ScaleIOPersistentVolumeSource | None = Field(
        default=None,
        alias="scaleIO",
        description="scaleIO represents a ScaleIO persistent volume attached and mounted on Kubernetes nodes. Deprecated: ScaleIO is deprecated and the in-tree scaleIO type is no longer supported.",
    )
    storage_class_name: str | None = Field(
        default=None,
        alias="storageClassName",
        description="storageClassName is the name of StorageClass to which this persistent volume belongs. Empty value means that this volume does not belong to any StorageClass.",
    )
    storageos: StorageOSPersistentVolumeSource | None = Field(
        default=None,
        alias="storageos",
        description="storageOS represents a StorageOS volume that is attached to the kubelet's host machine and mounted into the pod. Deprecated: StorageOS is deprecated and the in-tree storageos type is no longer supported. More info: https://examples.k8s.io/volumes/storageos/README.md",
    )
    volume_attributes_class_name: str | None = Field(
        default=None,
        alias="volumeAttributesClassName",
        description="Name of VolumeAttributesClass to which this persistent volume belongs. Empty value is not allowed. When this field is not set, it indicates that this volume does not belong to any VolumeAttributesClass. This field is mutable and can be changed by the CSI driver after a volume has been updated successfully to a new class. For an unbound PersistentVolume, the volumeAttributesClassName will be matched with unbound PersistentVolumeClaims during the binding process. This is a beta field and requires enabling VolumeAttributesClass feature (off by default).",
    )
    volume_mode: str | None = Field(
        default=None,
        alias="volumeMode",
        description="volumeMode defines if a volume is intended to be used with a formatted filesystem or to remain in raw block state. Value of Filesystem is implied when not included in spec.",
    )
    vsphere_volume: VsphereVirtualDiskVolumeSource | None = Field(
        default=None,
        alias="vsphereVolume",
        description="vsphereVolume represents a vSphere volume attached and mounted on kubelets host machine. Deprecated: VsphereVolume is deprecated. All operations for the in-tree vsphereVolume type are redirected to the csi.vsphere.vmware.com CSI driver.",
    )
