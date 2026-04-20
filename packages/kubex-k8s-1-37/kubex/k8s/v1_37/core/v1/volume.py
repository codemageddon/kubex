from pydantic import Field

from kubex.k8s.v1_37.core.v1.aws_elastic_block_store_volume_source import (
    AWSElasticBlockStoreVolumeSource,
)
from kubex.k8s.v1_37.core.v1.azure_disk_volume_source import AzureDiskVolumeSource
from kubex.k8s.v1_37.core.v1.azure_file_volume_source import AzureFileVolumeSource
from kubex.k8s.v1_37.core.v1.ceph_fs_volume_source import CephFSVolumeSource
from kubex.k8s.v1_37.core.v1.cinder_volume_source import CinderVolumeSource
from kubex.k8s.v1_37.core.v1.config_map_volume_source import ConfigMapVolumeSource
from kubex.k8s.v1_37.core.v1.csi_volume_source import CSIVolumeSource
from kubex.k8s.v1_37.core.v1.downward_api_volume_source import DownwardAPIVolumeSource
from kubex.k8s.v1_37.core.v1.empty_dir_volume_source import EmptyDirVolumeSource
from kubex.k8s.v1_37.core.v1.ephemeral_volume_source import EphemeralVolumeSource
from kubex.k8s.v1_37.core.v1.fc_volume_source import FCVolumeSource
from kubex.k8s.v1_37.core.v1.flex_volume_source import FlexVolumeSource
from kubex.k8s.v1_37.core.v1.flocker_volume_source import FlockerVolumeSource
from kubex.k8s.v1_37.core.v1.gce_persistent_disk_volume_source import (
    GCEPersistentDiskVolumeSource,
)
from kubex.k8s.v1_37.core.v1.git_repo_volume_source import GitRepoVolumeSource
from kubex.k8s.v1_37.core.v1.glusterfs_volume_source import GlusterfsVolumeSource
from kubex.k8s.v1_37.core.v1.host_path_volume_source import HostPathVolumeSource
from kubex.k8s.v1_37.core.v1.image_volume_source import ImageVolumeSource
from kubex.k8s.v1_37.core.v1.iscsi_volume_source import ISCSIVolumeSource
from kubex.k8s.v1_37.core.v1.nfs_volume_source import NFSVolumeSource
from kubex.k8s.v1_37.core.v1.persistent_volume_claim_volume_source import (
    PersistentVolumeClaimVolumeSource,
)
from kubex.k8s.v1_37.core.v1.photon_persistent_disk_volume_source import (
    PhotonPersistentDiskVolumeSource,
)
from kubex.k8s.v1_37.core.v1.portworx_volume_source import PortworxVolumeSource
from kubex.k8s.v1_37.core.v1.projected_volume_source import ProjectedVolumeSource
from kubex.k8s.v1_37.core.v1.quobyte_volume_source import QuobyteVolumeSource
from kubex.k8s.v1_37.core.v1.rbd_volume_source import RBDVolumeSource
from kubex.k8s.v1_37.core.v1.scale_io_volume_source import ScaleIOVolumeSource
from kubex.k8s.v1_37.core.v1.secret_volume_source import SecretVolumeSource
from kubex.k8s.v1_37.core.v1.storage_os_volume_source import StorageOSVolumeSource
from kubex.k8s.v1_37.core.v1.vsphere_virtual_disk_volume_source import (
    VsphereVirtualDiskVolumeSource,
)
from kubex_core.models.base import BaseK8sModel


class Volume(BaseK8sModel):
    """Volume represents a named volume in a pod that may be accessed by any container in the pod."""

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
    azure_file: AzureFileVolumeSource | None = Field(
        default=None,
        alias="azureFile",
        description="azureFile represents an Azure File Service mount on the host and bind mount to the pod. Deprecated: AzureFile is deprecated. All operations for the in-tree azureFile type are redirected to the file.csi.azure.com CSI driver.",
    )
    cephfs: CephFSVolumeSource | None = Field(
        default=None,
        alias="cephfs",
        description="cephFS represents a Ceph FS mount on the host that shares a pod's lifetime. Deprecated: CephFS is deprecated and the in-tree cephfs type is no longer supported.",
    )
    cinder: CinderVolumeSource | None = Field(
        default=None,
        alias="cinder",
        description="cinder represents a cinder volume attached and mounted on kubelets host machine. Deprecated: Cinder is deprecated. All operations for the in-tree cinder type are redirected to the cinder.csi.openstack.org CSI driver. More info: https://examples.k8s.io/mysql-cinder-pd/README.md",
    )
    config_map: ConfigMapVolumeSource | None = Field(
        default=None,
        alias="configMap",
        description="configMap represents a configMap that should populate this volume",
    )
    csi: CSIVolumeSource | None = Field(
        default=None,
        alias="csi",
        description="csi (Container Storage Interface) represents ephemeral storage that is handled by certain external CSI drivers.",
    )
    downward_api: DownwardAPIVolumeSource | None = Field(
        default=None,
        alias="downwardAPI",
        description="downwardAPI represents downward API about the pod that should populate this volume",
    )
    empty_dir: EmptyDirVolumeSource | None = Field(
        default=None,
        alias="emptyDir",
        description="emptyDir represents a temporary directory that shares a pod's lifetime. More info: https://kubernetes.io/docs/concepts/storage/volumes#emptydir",
    )
    ephemeral: EphemeralVolumeSource | None = Field(
        default=None,
        alias="ephemeral",
        description="ephemeral represents a volume that is handled by a cluster storage driver. The volume's lifecycle is tied to the pod that defines it - it will be created before the pod starts, and deleted when the pod is removed. Use this if: a) the volume is only needed while the pod runs, b) features of normal volumes like restoring from snapshot or capacity tracking are needed, c) the storage driver is specified through a storage class, and d) the storage driver supports dynamic volume provisioning through a PersistentVolumeClaim (see EphemeralVolumeSource for more information on the connection between this volume type and PersistentVolumeClaim). Use PersistentVolumeClaim or one of the vendor-specific APIs for volumes that persist for longer than the lifecycle of an individual pod. Use CSI for light-weight local ephemeral volumes if the CSI driver is meant to be used that way - see the documentation of the driver for more information. A pod can use both types of ephemeral volumes and persistent volumes at the same time.",
    )
    fc: FCVolumeSource | None = Field(
        default=None,
        alias="fc",
        description="fc represents a Fibre Channel resource that is attached to a kubelet's host machine and then exposed to the pod.",
    )
    flex_volume: FlexVolumeSource | None = Field(
        default=None,
        alias="flexVolume",
        description="flexVolume represents a generic volume resource that is provisioned/attached using an exec based plugin. Deprecated: FlexVolume is deprecated. Consider using a CSIDriver instead.",
    )
    flocker: FlockerVolumeSource | None = Field(
        default=None,
        alias="flocker",
        description="flocker represents a Flocker volume attached to a kubelet's host machine. This depends on the Flocker control service being running. Deprecated: Flocker is deprecated and the in-tree flocker type is no longer supported.",
    )
    gce_persistent_disk: GCEPersistentDiskVolumeSource | None = Field(
        default=None,
        alias="gcePersistentDisk",
        description="gcePersistentDisk represents a GCE Disk resource that is attached to a kubelet's host machine and then exposed to the pod. Deprecated: GCEPersistentDisk is deprecated. All operations for the in-tree gcePersistentDisk type are redirected to the pd.csi.storage.gke.io CSI driver. More info: https://kubernetes.io/docs/concepts/storage/volumes#gcepersistentdisk",
    )
    git_repo: GitRepoVolumeSource | None = Field(
        default=None,
        alias="gitRepo",
        description="gitRepo represents a git repository at a particular revision. Deprecated: GitRepo is deprecated. To provision a container with a git repo, mount an EmptyDir into an InitContainer that clones the repo using git, then mount the EmptyDir into the Pod's container.",
    )
    glusterfs: GlusterfsVolumeSource | None = Field(
        default=None,
        alias="glusterfs",
        description="glusterfs represents a Glusterfs mount on the host that shares a pod's lifetime. Deprecated: Glusterfs is deprecated and the in-tree glusterfs type is no longer supported.",
    )
    host_path: HostPathVolumeSource | None = Field(
        default=None,
        alias="hostPath",
        description="hostPath represents a pre-existing file or directory on the host machine that is directly exposed to the container. This is generally used for system agents or other privileged things that are allowed to see the host machine. Most containers will NOT need this. More info: https://kubernetes.io/docs/concepts/storage/volumes#hostpath",
    )
    image: ImageVolumeSource | None = Field(
        default=None,
        alias="image",
        description="image represents an OCI object (a container image or artifact) pulled and mounted on the kubelet's host machine. The volume is resolved at pod startup depending on which PullPolicy value is provided: - Always: the kubelet always attempts to pull the reference. Container creation will fail If the pull fails. - Never: the kubelet never pulls the reference and only uses a local image or artifact. Container creation will fail if the reference isn't present. - IfNotPresent: the kubelet pulls if the reference isn't already present on disk. Container creation will fail if the reference isn't present and the pull fails. The volume gets re-resolved if the pod gets deleted and recreated, which means that new remote content will become available on pod recreation. A failure to resolve or pull the image during pod startup will block containers from starting and may add significant latency. Failures will be retried using normal volume backoff and will be reported on the pod reason and message. The types of objects that may be mounted by this volume are defined by the container runtime implementation on a host machine and at minimum must include all valid types supported by the container image field. The OCI object gets mounted in a single directory (spec.containers[*].volumeMounts.mountPath) by merging the manifest layers in the same way as for container images. The volume will be mounted read-only (ro). Sub path mounts for containers are not supported (spec.containers[*].volumeMounts.subpath) before 1.33. The field spec.securityContext.fsGroupChangePolicy has no effect on this volume type.",
    )
    iscsi: ISCSIVolumeSource | None = Field(
        default=None,
        alias="iscsi",
        description="iscsi represents an ISCSI Disk resource that is attached to a kubelet's host machine and then exposed to the pod. More info: https://kubernetes.io/docs/concepts/storage/volumes/#iscsi",
    )
    name: str = Field(
        ...,
        alias="name",
        description="name of the volume. Must be a DNS_LABEL and unique within the pod. More info: https://kubernetes.io/docs/concepts/overview/working-with-objects/names/#names",
    )
    nfs: NFSVolumeSource | None = Field(
        default=None,
        alias="nfs",
        description="nfs represents an NFS mount on the host that shares a pod's lifetime More info: https://kubernetes.io/docs/concepts/storage/volumes#nfs",
    )
    persistent_volume_claim: PersistentVolumeClaimVolumeSource | None = Field(
        default=None,
        alias="persistentVolumeClaim",
        description="persistentVolumeClaimVolumeSource represents a reference to a PersistentVolumeClaim in the same namespace. More info: https://kubernetes.io/docs/concepts/storage/persistent-volumes#persistentvolumeclaims",
    )
    photon_persistent_disk: PhotonPersistentDiskVolumeSource | None = Field(
        default=None,
        alias="photonPersistentDisk",
        description="photonPersistentDisk represents a PhotonController persistent disk attached and mounted on kubelets host machine. Deprecated: PhotonPersistentDisk is deprecated and the in-tree photonPersistentDisk type is no longer supported.",
    )
    portworx_volume: PortworxVolumeSource | None = Field(
        default=None,
        alias="portworxVolume",
        description="portworxVolume represents a portworx volume attached and mounted on kubelets host machine. Deprecated: PortworxVolume is deprecated. All operations for the in-tree portworxVolume type are redirected to the pxd.portworx.com CSI driver.",
    )
    projected: ProjectedVolumeSource | None = Field(
        default=None,
        alias="projected",
        description="projected items for all in one resources secrets, configmaps, and downward API",
    )
    quobyte: QuobyteVolumeSource | None = Field(
        default=None,
        alias="quobyte",
        description="quobyte represents a Quobyte mount on the host that shares a pod's lifetime. Deprecated: Quobyte is deprecated and the in-tree quobyte type is no longer supported.",
    )
    rbd: RBDVolumeSource | None = Field(
        default=None,
        alias="rbd",
        description="rbd represents a Rados Block Device mount on the host that shares a pod's lifetime. Deprecated: RBD is deprecated and the in-tree rbd type is no longer supported.",
    )
    scale_io: ScaleIOVolumeSource | None = Field(
        default=None,
        alias="scaleIO",
        description="scaleIO represents a ScaleIO persistent volume attached and mounted on Kubernetes nodes. Deprecated: ScaleIO is deprecated and the in-tree scaleIO type is no longer supported.",
    )
    secret: SecretVolumeSource | None = Field(
        default=None,
        alias="secret",
        description="secret represents a secret that should populate this volume. More info: https://kubernetes.io/docs/concepts/storage/volumes#secret",
    )
    storageos: StorageOSVolumeSource | None = Field(
        default=None,
        alias="storageos",
        description="storageOS represents a StorageOS volume attached and mounted on Kubernetes nodes. Deprecated: StorageOS is deprecated and the in-tree storageos type is no longer supported.",
    )
    vsphere_volume: VsphereVirtualDiskVolumeSource | None = Field(
        default=None,
        alias="vsphereVolume",
        description="vsphereVolume represents a vSphere volume attached and mounted on kubelets host machine. Deprecated: VsphereVolume is deprecated. All operations for the in-tree vsphereVolume type are redirected to the csi.vsphere.vmware.com CSI driver.",
    )
