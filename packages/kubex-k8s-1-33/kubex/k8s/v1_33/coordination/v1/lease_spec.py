import datetime

from pydantic import Field

from kubex_core.models.base import BaseK8sModel


class LeaseSpec(BaseK8sModel):
    """LeaseSpec is a specification of a Lease."""

    acquire_time: datetime.datetime | None = Field(
        default=None,
        alias="acquireTime",
        description="acquireTime is a time when the current lease was acquired.",
    )
    holder_identity: str | None = Field(
        default=None,
        alias="holderIdentity",
        description="holderIdentity contains the identity of the holder of a current lease. If Coordinated Leader Election is used, the holder identity must be equal to the elected LeaseCandidate.metadata.name field.",
    )
    lease_duration_seconds: int | None = Field(
        default=None,
        alias="leaseDurationSeconds",
        description="leaseDurationSeconds is a duration that candidates for a lease need to wait to force acquire it. This is measured against the time of last observed renewTime.",
    )
    lease_transitions: int | None = Field(
        default=None,
        alias="leaseTransitions",
        description="leaseTransitions is the number of transitions of a lease between holders.",
    )
    preferred_holder: str | None = Field(
        default=None,
        alias="preferredHolder",
        description="PreferredHolder signals to a lease holder that the lease has a more optimal holder and should be given up. This field can only be set if Strategy is also set.",
    )
    renew_time: datetime.datetime | None = Field(
        default=None,
        alias="renewTime",
        description="renewTime is a time when the current holder of a lease has last updated the lease.",
    )
    strategy: str | None = Field(
        default=None,
        alias="strategy",
        description="Strategy indicates the strategy for picking the leader for coordinated leader election. If the field is not specified, there is no active coordination for this lease. (Alpha) Using this field requires the CoordinatedLeaderElection feature gate to be enabled.",
    )
