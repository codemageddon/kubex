from kubex.k8s.v1_34.apps.v1.deployment_strategy import DeploymentStrategy
from kubex.k8s.v1_34.core.v1.pod_template_spec import PodTemplateSpec
from kubex.k8s.v1_34.meta.v1.label_selector import LabelSelector
from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class DeploymentSpec(BaseK8sModel):
    """DeploymentSpec is the specification of the desired behavior of the Deployment."""

    min_ready_seconds: int | None = Field(
        default=None,
        alias="minReadySeconds",
        description="Minimum number of seconds for which a newly created pod should be ready without any of its container crashing, for it to be considered available. Defaults to 0 (pod will be considered available as soon as it is ready)",
    )
    paused: bool | None = Field(
        default=None,
        alias="paused",
        description="Indicates that the deployment is paused.",
    )
    progress_deadline_seconds: int | None = Field(
        default=None,
        alias="progressDeadlineSeconds",
        description="The maximum time in seconds for a deployment to make progress before it is considered to be failed. The deployment controller will continue to process failed deployments and a condition with a ProgressDeadlineExceeded reason will be surfaced in the deployment status. Note that progress will not be estimated during the time a deployment is paused. Defaults to 600s.",
    )
    replicas: int | None = Field(
        default=None,
        alias="replicas",
        description="Number of desired pods. This is a pointer to distinguish between explicit zero and not specified. Defaults to 1.",
    )
    revision_history_limit: int | None = Field(
        default=None,
        alias="revisionHistoryLimit",
        description="The number of old ReplicaSets to retain to allow rollback. This is a pointer to distinguish between explicit zero and not specified. Defaults to 10.",
    )
    selector: LabelSelector = Field(
        ...,
        alias="selector",
        description="Label selector for pods. Existing ReplicaSets whose pods are selected by this will be the ones affected by this deployment. It must match the pod template's labels.",
    )
    strategy: DeploymentStrategy | None = Field(
        default=None,
        alias="strategy",
        description="The deployment strategy to use to replace existing pods with new ones.",
    )
    template: PodTemplateSpec = Field(
        ...,
        alias="template",
        description='Template describes the pods that will be created. The only allowed template.spec.restartPolicy value is "Always".',
    )
