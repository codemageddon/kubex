from pydantic import Field

from kubex_core.models.base import BaseK8sModel


class GroupResource(BaseK8sModel):
    """GroupResource specifies a Group and a Resource, but does not force a version. This is useful for identifying concepts during lookup stages without having partially valid types"""

    group: str = Field(..., alias="group")
    resource: str = Field(..., alias="resource")
