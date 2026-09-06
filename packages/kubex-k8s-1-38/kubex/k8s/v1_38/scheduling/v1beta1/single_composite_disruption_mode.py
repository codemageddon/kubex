from kubex_core.models.base import BaseK8sModel


class SingleCompositeDisruptionMode(BaseK8sModel):
    """SingleCompositeDisruptionMode means that individual children of a CompositePodGroup can be disrupted or preempted independently."""
