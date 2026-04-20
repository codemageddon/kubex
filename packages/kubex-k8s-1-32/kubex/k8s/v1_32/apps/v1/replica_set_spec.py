from pydantic import Field

from kubex.k8s.v1_32.core.v1.pod_template_spec import PodTemplateSpec
from kubex.k8s.v1_32.meta.v1.label_selector import LabelSelector
from kubex_core.models.base import BaseK8sModel


class ReplicaSetSpec(BaseK8sModel):
    """ReplicaSetSpec is the specification of a ReplicaSet."""

    min_ready_seconds: int | None = Field(
        default=None,
        alias="minReadySeconds",
        description="Minimum number of seconds for which a newly created pod should be ready without any of its container crashing, for it to be considered available. Defaults to 0 (pod will be considered available as soon as it is ready)",
    )
    replicas: int | None = Field(
        default=None,
        alias="replicas",
        description="Replicas is the number of desired replicas. This is a pointer to distinguish between explicit zero and unspecified. Defaults to 1. More info: https://kubernetes.io/docs/concepts/workloads/controllers/replicationcontroller/#what-is-a-replicationcontroller",
    )
    selector: LabelSelector = Field(
        ...,
        alias="selector",
        description="Selector is a label query over pods that should match the replica count. Label keys and values that must match in order to be controlled by this replica set. It must match the pod template's labels. More info: https://kubernetes.io/docs/concepts/overview/working-with-objects/labels/#label-selectors",
    )
    template: PodTemplateSpec | None = Field(
        default=None,
        alias="template",
        description="Template is the object that describes the pod that will be created if insufficient replicas are detected. More info: https://kubernetes.io/docs/concepts/workloads/controllers/replicationcontroller#pod-template",
    )
