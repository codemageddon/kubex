from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class Sysctl(BaseK8sModel):
    """Sysctl defines a kernel parameter to be set"""

    name: str = Field(..., alias="name", description="Name of a property to set")
    value: str = Field(..., alias="value", description="Value of a property to set")
