from pydantic import Field

from kubex_core.models.base import BaseK8sModel
from kubex_core.models.types import Quantity


class Overhead(BaseK8sModel):
    """Overhead structure represents the resource overhead associated with running a pod."""

    pod_fixed: dict[str, Quantity] | None = Field(
        default=None,
        alias="podFixed",
        description="podFixed represents the fixed resource overhead associated with running a pod.",
    )
