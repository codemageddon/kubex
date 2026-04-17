import datetime

from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class CertificateSigningRequestCondition(BaseK8sModel):
    """CertificateSigningRequestCondition describes a condition of a CertificateSigningRequest object"""

    last_transition_time: datetime.datetime | None = Field(
        default=None,
        alias="lastTransitionTime",
        description="lastTransitionTime is the time the condition last transitioned from one status to another. If unset, when a new condition type is added or an existing condition's status is changed, the server defaults this to the current time.",
    )
    last_update_time: datetime.datetime | None = Field(
        default=None,
        alias="lastUpdateTime",
        description="lastUpdateTime is the time of the last update to this condition",
    )
    message: str | None = Field(
        default=None,
        alias="message",
        description="message contains a human readable message with details about the request state",
    )
    reason: str | None = Field(
        default=None,
        alias="reason",
        description="reason indicates a brief reason for the request state",
    )
    status: str = Field(
        ...,
        alias="status",
        description='status of the condition, one of True, False, Unknown. Approved, Denied, and Failed conditions may not be "False" or "Unknown".',
    )
    type_: str = Field(
        ...,
        alias="type",
        description='type of the condition. Known conditions are "Approved", "Denied", and "Failed". An "Approved" condition is added via the /approval subresource, indicating the request was approved and should be issued by the signer. A "Denied" condition is added via the /approval subresource, indicating the request was denied and should not be issued by the signer. A "Failed" condition is added via the /status subresource, indicating the signer failed to issue the certificate. Approved and Denied conditions are mutually exclusive. Approved, Denied, and Failed conditions cannot be removed once added. Only one condition of a given type is allowed.',
    )
