from kubex_core.models.base import BaseK8sModel


class AllCompositeDisruptionMode(BaseK8sModel):
    """AllCompositeDisruptionMode means that children of a CompositePodGroup can only be disrupted or preempted together."""
