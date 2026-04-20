from pydantic import Field

from kubex.k8s.v1_37.core.v1.persistent_volume_claim_spec import (
    PersistentVolumeClaimSpec,
)
from kubex_core.models.base import BaseK8sModel
from kubex_core.models.metadata import ObjectMetadata


class PersistentVolumeClaimTemplate(BaseK8sModel):
    """PersistentVolumeClaimTemplate is used to produce PersistentVolumeClaim objects as part of an EphemeralVolumeSource."""

    metadata: ObjectMetadata | None = Field(
        default=None,
        alias="metadata",
        description="May contain labels and annotations that will be copied into the PVC when creating it. No other fields are allowed and will be rejected during validation.",
    )
    spec: PersistentVolumeClaimSpec = Field(
        ...,
        alias="spec",
        description="The specification for the PersistentVolumeClaim. The entire content is copied unchanged into the PVC that gets created from this template. The same fields as in a PersistentVolumeClaim are also valid here.",
    )
