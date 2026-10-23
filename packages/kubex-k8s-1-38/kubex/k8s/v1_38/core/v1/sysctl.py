from pydantic import Field

from kubex_core.models.base import BaseK8sModel


class Sysctl(BaseK8sModel):
    """Sysctl defines a kernel parameter to be set"""

    name: str = Field(..., alias="name", description="name of a property to set")
    value: str = Field(..., alias="value", description="value of a property to set")
