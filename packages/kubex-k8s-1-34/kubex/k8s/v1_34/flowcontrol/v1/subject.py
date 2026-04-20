from pydantic import Field

from kubex.k8s.v1_34.flowcontrol.v1.group_subject import GroupSubject
from kubex.k8s.v1_34.flowcontrol.v1.service_account_subject import ServiceAccountSubject
from kubex.k8s.v1_34.flowcontrol.v1.user_subject import UserSubject
from kubex_core.models.base import BaseK8sModel


class Subject(BaseK8sModel):
    """Subject matches the originator of a request, as identified by the request authentication system. There are three ways of matching an originator; by user, group, or service account."""

    group: GroupSubject | None = Field(
        default=None,
        alias="group",
        description="`group` matches based on user group name.",
    )
    kind: str = Field(
        ...,
        alias="kind",
        description="`kind` indicates which one of the other fields is non-empty. Required",
    )
    service_account: ServiceAccountSubject | None = Field(
        default=None,
        alias="serviceAccount",
        description="`serviceAccount` matches ServiceAccounts.",
    )
    user: UserSubject | None = Field(
        default=None, alias="user", description="`user` matches based on username."
    )
