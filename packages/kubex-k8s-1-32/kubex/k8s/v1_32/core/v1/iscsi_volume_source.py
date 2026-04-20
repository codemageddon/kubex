from pydantic import Field

from kubex.k8s.v1_32.core.v1.local_object_reference import LocalObjectReference
from kubex_core.models.base import BaseK8sModel


class ISCSIVolumeSource(BaseK8sModel):
    """Represents an ISCSI disk. ISCSI volumes can only be mounted as read/write once. ISCSI volumes support ownership management and SELinux relabeling."""

    chap_auth_discovery: bool | None = Field(
        default=None,
        alias="chapAuthDiscovery",
        description="chapAuthDiscovery defines whether support iSCSI Discovery CHAP authentication",
    )
    chap_auth_session: bool | None = Field(
        default=None,
        alias="chapAuthSession",
        description="chapAuthSession defines whether support iSCSI Session CHAP authentication",
    )
    fs_type: str | None = Field(
        default=None,
        alias="fsType",
        description='fsType is the filesystem type of the volume that you want to mount. Tip: Ensure that the filesystem type is supported by the host operating system. Examples: "ext4", "xfs", "ntfs". Implicitly inferred to be "ext4" if unspecified. More info: https://kubernetes.io/docs/concepts/storage/volumes#iscsi',
    )
    initiator_name: str | None = Field(
        default=None,
        alias="initiatorName",
        description="initiatorName is the custom iSCSI Initiator Name. If initiatorName is specified with iscsiInterface simultaneously, new iSCSI interface <target portal>:<volume name> will be created for the connection.",
    )
    iqn: str = Field(
        ..., alias="iqn", description="iqn is the target iSCSI Qualified Name."
    )
    iscsi_interface: str | None = Field(
        default=None,
        alias="iscsiInterface",
        description="iscsiInterface is the interface Name that uses an iSCSI transport. Defaults to 'default' (tcp).",
    )
    lun: int = Field(
        ..., alias="lun", description="lun represents iSCSI Target Lun number."
    )
    portals: list[str] | None = Field(
        default=None,
        alias="portals",
        description="portals is the iSCSI Target Portal List. The portal is either an IP or ip_addr:port if the port is other than default (typically TCP ports 860 and 3260).",
    )
    read_only: bool | None = Field(
        default=None,
        alias="readOnly",
        description="readOnly here will force the ReadOnly setting in VolumeMounts. Defaults to false.",
    )
    secret_ref: LocalObjectReference | None = Field(
        default=None,
        alias="secretRef",
        description="secretRef is the CHAP Secret for iSCSI target and initiator authentication",
    )
    target_portal: str = Field(
        ...,
        alias="targetPortal",
        description="targetPortal is iSCSI Target Portal. The Portal is either an IP or ip_addr:port if the port is other than default (typically TCP ports 860 and 3260).",
    )
