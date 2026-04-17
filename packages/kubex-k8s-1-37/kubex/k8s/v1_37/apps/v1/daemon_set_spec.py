from kubex.k8s.v1_37.apps.v1.daemon_set_update_strategy import DaemonSetUpdateStrategy
from kubex.k8s.v1_37.core.v1.pod_template_spec import PodTemplateSpec
from kubex.k8s.v1_37.meta.v1.label_selector import LabelSelector
from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class DaemonSetSpec(BaseK8sModel):
    """DaemonSetSpec is the specification of a daemon set."""

    min_ready_seconds: int | None = Field(
        default=None,
        alias="minReadySeconds",
        description="The minimum number of seconds for which a newly created DaemonSet pod should be ready without any of its container crashing, for it to be considered available. Defaults to 0 (pod will be considered available as soon as it is ready).",
    )
    revision_history_limit: int | None = Field(
        default=None,
        alias="revisionHistoryLimit",
        description="The number of old history to retain to allow rollback. This is a pointer to distinguish between explicit zero and not specified. Defaults to 10.",
    )
    selector: LabelSelector = Field(
        ...,
        alias="selector",
        description="A label query over pods that are managed by the daemon set. Must match in order to be controlled. It must match the pod template's labels. More info: https://kubernetes.io/docs/concepts/overview/working-with-objects/labels/#label-selectors",
    )
    template: PodTemplateSpec = Field(
        ...,
        alias="template",
        description='An object that describes the pod that will be created. The DaemonSet will create exactly one copy of this pod on every node that matches the template\'s node selector (or on every node if no node selector is specified). The only allowed template.spec.restartPolicy value is "Always". More info: https://kubernetes.io/docs/concepts/workloads/controllers/replicationcontroller#pod-template',
    )
    update_strategy: DaemonSetUpdateStrategy | None = Field(
        default=None,
        alias="updateStrategy",
        description="An update strategy to replace existing DaemonSet pods with new pods.",
    )
