from kubex.k8s.v1_37.apps.v1.stateful_set_ordinals import StatefulSetOrdinals
from kubex.k8s.v1_37.apps.v1.stateful_set_persistent_volume_claim_retention_policy import (
    StatefulSetPersistentVolumeClaimRetentionPolicy,
)
from kubex.k8s.v1_37.apps.v1.stateful_set_update_strategy import (
    StatefulSetUpdateStrategy,
)
from kubex.k8s.v1_37.core.v1.persistent_volume_claim import PersistentVolumeClaim
from kubex.k8s.v1_37.core.v1.pod_template_spec import PodTemplateSpec
from kubex.k8s.v1_37.meta.v1.label_selector import LabelSelector
from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class StatefulSetSpec(BaseK8sModel):
    """A StatefulSetSpec is the specification of a StatefulSet."""

    min_ready_seconds: int | None = Field(
        default=None,
        alias="minReadySeconds",
        description="Minimum number of seconds for which a newly created pod should be ready without any of its container crashing for it to be considered available. Defaults to 0 (pod will be considered available as soon as it is ready)",
    )
    ordinals: StatefulSetOrdinals | None = Field(
        default=None,
        alias="ordinals",
        description='ordinals controls the numbering of replica indices in a StatefulSet. The default ordinals behavior assigns a "0" index to the first replica and increments the index by one for each additional replica requested.',
    )
    persistent_volume_claim_retention_policy: (
        StatefulSetPersistentVolumeClaimRetentionPolicy | None
    ) = Field(
        default=None,
        alias="persistentVolumeClaimRetentionPolicy",
        description="persistentVolumeClaimRetentionPolicy describes the lifecycle of persistent volume claims created from volumeClaimTemplates. By default, all persistent volume claims are created as needed and retained until manually deleted. This policy allows the lifecycle to be altered, for example by deleting persistent volume claims when their stateful set is deleted, or when their pod is scaled down.",
    )
    pod_management_policy: str | None = Field(
        default=None,
        alias="podManagementPolicy",
        description="podManagementPolicy controls how pods are created during initial scale up, when replacing pods on nodes, or when scaling down. The default policy is `OrderedReady`, where pods are created in increasing order (pod-0, then pod-1, etc) and the controller will wait until each pod is ready before continuing. When scaling down, the pods are removed in the opposite order. The alternative policy is `Parallel` which will create pods in parallel to match the desired scale without waiting, and on scale down will delete all pods at once.",
    )
    replicas: int | None = Field(
        default=None,
        alias="replicas",
        description="replicas is the desired number of replicas of the given Template. These are replicas in the sense that they are instantiations of the same Template, but individual replicas also have a consistent identity. If unspecified, defaults to 1.",
    )
    revision_history_limit: int | None = Field(
        default=None,
        alias="revisionHistoryLimit",
        description="revisionHistoryLimit is the maximum number of revisions that will be maintained in the StatefulSet's revision history. The revision history consists of all revisions not represented by a currently applied StatefulSetSpec version. The default value is 10.",
    )
    selector: LabelSelector = Field(
        ...,
        alias="selector",
        description="selector is a label query over pods that should match the replica count. It must match the pod template's labels. More info: https://kubernetes.io/docs/concepts/overview/working-with-objects/labels/#label-selectors",
    )
    service_name: str | None = Field(
        default=None,
        alias="serviceName",
        description='serviceName is the name of the service that governs this StatefulSet. This service must exist before the StatefulSet, and is responsible for the network identity of the set. Pods get DNS/hostnames that follow the pattern: pod-specific-string.serviceName.default.svc.cluster.local where "pod-specific-string" is managed by the StatefulSet controller.',
    )
    template: PodTemplateSpec = Field(
        ...,
        alias="template",
        description='template is the object that describes the pod that will be created if insufficient replicas are detected. Each pod stamped out by the StatefulSet will fulfill this Template, but have a unique identity from the rest of the StatefulSet. Each pod will be named with the format <statefulsetname>-<podindex>. For example, a pod in a StatefulSet named "web" with index number "3" would be named "web-3". The only allowed template.spec.restartPolicy value is "Always".',
    )
    update_strategy: StatefulSetUpdateStrategy | None = Field(
        default=None,
        alias="updateStrategy",
        description="updateStrategy indicates the StatefulSetUpdateStrategy that will be employed to update Pods in the StatefulSet when a revision is made to Template.",
    )
    volume_claim_templates: list[PersistentVolumeClaim] | None = Field(
        default=None,
        alias="volumeClaimTemplates",
        description="volumeClaimTemplates is a list of claims that pods are allowed to reference. The StatefulSet controller is responsible for mapping network identities to claims in a way that maintains the identity of a pod. Every claim in this list must have at least one matching (by name) volumeMount in one container in the template. A claim in this list takes precedence over any volumes in the template, with the same name.",
    )
