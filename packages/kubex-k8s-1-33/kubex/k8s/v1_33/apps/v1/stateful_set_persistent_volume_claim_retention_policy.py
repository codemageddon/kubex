from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class StatefulSetPersistentVolumeClaimRetentionPolicy(BaseK8sModel):
    """StatefulSetPersistentVolumeClaimRetentionPolicy describes the policy used for PVCs created from the StatefulSet VolumeClaimTemplates."""

    when_deleted: str | None = Field(
        default=None,
        alias="whenDeleted",
        description="WhenDeleted specifies what happens to PVCs created from StatefulSet VolumeClaimTemplates when the StatefulSet is deleted. The default policy of `Retain` causes PVCs to not be affected by StatefulSet deletion. The `Delete` policy causes those PVCs to be deleted.",
    )
    when_scaled: str | None = Field(
        default=None,
        alias="whenScaled",
        description="WhenScaled specifies what happens to PVCs created from StatefulSet VolumeClaimTemplates when the StatefulSet is scaled down. The default policy of `Retain` causes PVCs to not be affected by a scaledown. The `Delete` policy causes the associated PVCs for any excess pods above the replica count to be deleted.",
    )
