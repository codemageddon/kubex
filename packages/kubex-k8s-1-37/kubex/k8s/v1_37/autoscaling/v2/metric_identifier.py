from pydantic import Field

from kubex.k8s.v1_37.meta.v1.label_selector import LabelSelector
from kubex_core.models.base import BaseK8sModel


class MetricIdentifier(BaseK8sModel):
    """MetricIdentifier defines the name and optionally selector for a metric"""

    name: str = Field(
        ..., alias="name", description="name is the name of the given metric"
    )
    selector: LabelSelector | None = Field(
        default=None,
        alias="selector",
        description="selector is the string-encoded form of a standard kubernetes label selector for the given metric When set, it is passed as an additional parameter to the metrics server for more specific metrics scoping. When unset, just the metricName will be used to gather metrics.",
    )
