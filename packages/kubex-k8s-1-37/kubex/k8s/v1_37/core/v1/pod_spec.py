from kubex.k8s.v1_37.core.v1.affinity import Affinity
from kubex.k8s.v1_37.core.v1.container import Container
from kubex.k8s.v1_37.core.v1.ephemeral_container import EphemeralContainer
from kubex.k8s.v1_37.core.v1.host_alias import HostAlias
from kubex.k8s.v1_37.core.v1.local_object_reference import LocalObjectReference
from kubex.k8s.v1_37.core.v1.pod_dns_config import PodDNSConfig
from kubex.k8s.v1_37.core.v1.pod_os import PodOS
from kubex.k8s.v1_37.core.v1.pod_readiness_gate import PodReadinessGate
from kubex.k8s.v1_37.core.v1.pod_resource_claim import PodResourceClaim
from kubex.k8s.v1_37.core.v1.pod_scheduling_gate import PodSchedulingGate
from kubex.k8s.v1_37.core.v1.pod_scheduling_group import PodSchedulingGroup
from kubex.k8s.v1_37.core.v1.pod_security_context import PodSecurityContext
from kubex.k8s.v1_37.core.v1.resource_requirements import ResourceRequirements
from kubex.k8s.v1_37.core.v1.toleration import Toleration
from kubex.k8s.v1_37.core.v1.topology_spread_constraint import TopologySpreadConstraint
from kubex.k8s.v1_37.core.v1.volume import Volume
from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class PodSpec(BaseK8sModel):
    """PodSpec is a description of a pod."""

    active_deadline_seconds: int | None = Field(
        default=None,
        alias="activeDeadlineSeconds",
        description="Optional duration in seconds the pod may be active on the node relative to StartTime before the system will actively try to mark it failed and kill associated containers. Value must be a positive integer.",
    )
    affinity: Affinity | None = Field(
        default=None,
        alias="affinity",
        description="If specified, the pod's scheduling constraints",
    )
    automount_service_account_token: bool | None = Field(
        default=None,
        alias="automountServiceAccountToken",
        description="AutomountServiceAccountToken indicates whether a service account token should be automatically mounted.",
    )
    containers: list[Container] = Field(
        ...,
        alias="containers",
        description="List of containers belonging to the pod. Containers cannot currently be added or removed. There must be at least one container in a Pod. Cannot be updated.",
    )
    dns_config: PodDNSConfig | None = Field(
        default=None,
        alias="dnsConfig",
        description="Specifies the DNS parameters of a pod. Parameters specified here will be merged to the generated DNS configuration based on DNSPolicy.",
    )
    dns_policy: str | None = Field(
        default=None,
        alias="dnsPolicy",
        description="Set DNS policy for the pod. Defaults to \"ClusterFirst\". Valid values are 'ClusterFirstWithHostNet', 'ClusterFirst', 'Default' or 'None'. DNS parameters given in DNSConfig will be merged with the policy selected with DNSPolicy. To have DNS options set along with hostNetwork, you have to specify DNS policy explicitly to 'ClusterFirstWithHostNet'.",
    )
    enable_service_links: bool | None = Field(
        default=None,
        alias="enableServiceLinks",
        description="EnableServiceLinks indicates whether information about services should be injected into pod's environment variables, matching the syntax of Docker links. Optional: Defaults to true.",
    )
    ephemeral_containers: list[EphemeralContainer] | None = Field(
        default=None,
        alias="ephemeralContainers",
        description="List of ephemeral containers run in this pod. Ephemeral containers may be run in an existing pod to perform user-initiated actions such as debugging. This list cannot be specified when creating a pod, and it cannot be modified by updating the pod spec. In order to add an ephemeral container to an existing pod, use the pod's ephemeralcontainers subresource.",
    )
    host_aliases: list[HostAlias] | None = Field(
        default=None,
        alias="hostAliases",
        description="HostAliases is an optional list of hosts and IPs that will be injected into the pod's hosts file if specified.",
    )
    host_ipc: bool | None = Field(
        default=None,
        alias="hostIPC",
        description="Use the host's ipc namespace. Optional: Default to false.",
    )
    host_network: bool | None = Field(
        default=None,
        alias="hostNetwork",
        description="Host networking requested for this pod. Use the host's network namespace. When using HostNetwork you should specify ports so the scheduler is aware. When `hostNetwork` is true, specified `hostPort` fields in port definitions must match `containerPort`, and unspecified `hostPort` fields in port definitions are defaulted to match `containerPort`. Default to false.",
    )
    host_pid: bool | None = Field(
        default=None,
        alias="hostPID",
        description="Use the host's pid namespace. Optional: Default to false.",
    )
    host_users: bool | None = Field(
        default=None,
        alias="hostUsers",
        description="Use the host's user namespace. Optional: Default to true. If set to true or not present, the pod will be run in the host user namespace, useful for when the pod needs a feature only available to the host user namespace, such as loading a kernel module with CAP_SYS_MODULE. When set to false, a new userns is created for the pod. Setting false is useful for mitigating container breakout vulnerabilities even allowing users to run their containers as root without actually having root privileges on the host.",
    )
    hostname: str | None = Field(
        default=None,
        alias="hostname",
        description="Specifies the hostname of the Pod If not specified, the pod's hostname will be set to a system-defined value.",
    )
    hostname_override: str | None = Field(
        default=None,
        alias="hostnameOverride",
        description="HostnameOverride specifies an explicit override for the pod's hostname as perceived by the pod. This field only specifies the pod's hostname and does not affect its DNS records. When this field is set to a non-empty string: - It takes precedence over the values set in `hostname` and `subdomain`. - The Pod's hostname will be set to this value. - `setHostnameAsFQDN` must be nil or set to false. - `hostNetwork` must be set to false. This field must be a valid DNS subdomain as defined in RFC 1123 and contain at most 64 characters. Requires the HostnameOverride feature gate to be enabled.",
    )
    image_pull_secrets: list[LocalObjectReference] | None = Field(
        default=None,
        alias="imagePullSecrets",
        description="ImagePullSecrets is an optional list of references to secrets in the same namespace to use for pulling any of the images used by this PodSpec. If specified, these secrets will be passed to individual puller implementations for them to use. More info: https://kubernetes.io/docs/concepts/containers/images#specifying-imagepullsecrets-on-a-pod",
    )
    init_containers: list[Container] | None = Field(
        default=None,
        alias="initContainers",
        description="List of initialization containers belonging to the pod. Init containers are executed in order prior to containers being started. If any init container fails, the pod is considered to have failed and is handled according to its restartPolicy. The name for an init container or normal container must be unique among all containers. Init containers may not have Lifecycle actions, Readiness probes, Liveness probes, or Startup probes. The resourceRequirements of an init container are taken into account during scheduling by finding the highest request/limit for each resource type, and then using the max of that value or the sum of the normal containers. Limits are applied to init containers in a similar fashion. Init containers cannot currently be added or removed. Cannot be updated. More info: https://kubernetes.io/docs/concepts/workloads/pods/init-containers/",
    )
    node_name: str | None = Field(
        default=None,
        alias="nodeName",
        description="NodeName indicates in which node this pod is scheduled. If empty, this pod is a candidate for scheduling by the scheduler defined in schedulerName. Once this field is set, the kubelet for this node becomes responsible for the lifecycle of this pod. This field should not be used to express a desire for the pod to be scheduled on a specific node. https://kubernetes.io/docs/concepts/scheduling-eviction/assign-pod-node/#nodename",
    )
    node_selector: dict[str, str] | None = Field(
        default=None,
        alias="nodeSelector",
        description="NodeSelector is a selector which must be true for the pod to fit on a node. Selector which must match a node's labels for the pod to be scheduled on that node. More info: https://kubernetes.io/docs/concepts/configuration/assign-pod-node/",
    )
    os: PodOS | None = Field(
        default=None,
        alias="os",
        description="Specifies the OS of the containers in the pod. Some pod and container fields are restricted if this is set. If the OS field is set to linux, the following fields must be unset: -securityContext.windowsOptions If the OS field is set to windows, following fields must be unset: - spec.hostPID - spec.hostIPC - spec.hostUsers - spec.resources - spec.securityContext.appArmorProfile - spec.securityContext.seLinuxOptions - spec.securityContext.seccompProfile - spec.securityContext.fsGroup - spec.securityContext.fsGroupChangePolicy - spec.securityContext.sysctls - spec.shareProcessNamespace - spec.securityContext.runAsUser - spec.securityContext.runAsGroup - spec.securityContext.supplementalGroups - spec.securityContext.supplementalGroupsPolicy - spec.containers[*].securityContext.appArmorProfile - spec.containers[*].securityContext.seLinuxOptions - spec.containers[*].securityContext.seccompProfile - spec.containers[*].securityContext.capabilities - spec.containers[*].securityContext.readOnlyRootFilesystem - spec.containers[*].securityContext.privileged - spec.containers[*].securityContext.allowPrivilegeEscalation - spec.containers[*].securityContext.procMount - spec.containers[*].securityContext.runAsUser - spec.containers[*].securityContext.runAsGroup",
    )
    overhead: dict[str, str] | None = Field(
        default=None,
        alias="overhead",
        description="Overhead represents the resource overhead associated with running a pod for a given RuntimeClass. This field will be autopopulated at admission time by the RuntimeClass admission controller. If the RuntimeClass admission controller is enabled, overhead must not be set in Pod create requests. The RuntimeClass admission controller will reject Pod create requests which have the overhead already set. If RuntimeClass is configured and selected in the PodSpec, Overhead will be set to the value defined in the corresponding RuntimeClass, otherwise it will remain unset and treated as zero. More info: https://git.k8s.io/enhancements/keps/sig-node/688-pod-overhead/README.md",
    )
    preemption_policy: str | None = Field(
        default=None,
        alias="preemptionPolicy",
        description="PreemptionPolicy is the Policy for preempting pods with lower priority. One of Never, PreemptLowerPriority. Defaults to PreemptLowerPriority if unset.",
    )
    priority: int | None = Field(
        default=None,
        alias="priority",
        description="The priority value. Various system components use this field to find the priority of the pod. When Priority Admission Controller is enabled, it prevents users from setting this field. The admission controller populates this field from PriorityClassName. The higher the value, the higher the priority.",
    )
    priority_class_name: str | None = Field(
        default=None,
        alias="priorityClassName",
        description='If specified, indicates the pod\'s priority. "system-node-critical" and "system-cluster-critical" are two special keywords which indicate the highest priorities with the former being the highest priority. Any other name must be defined by creating a PriorityClass object with that name. If not specified, the pod priority will be default or zero if there is no default.',
    )
    readiness_gates: list[PodReadinessGate] | None = Field(
        default=None,
        alias="readinessGates",
        description='If specified, all readiness gates will be evaluated for pod readiness. A pod is ready when all its containers are ready AND all conditions specified in the readiness gates have status equal to "True" More info: https://git.k8s.io/enhancements/keps/sig-network/580-pod-readiness-gates',
    )
    resource_claims: list[PodResourceClaim] | None = Field(
        default=None,
        alias="resourceClaims",
        description="ResourceClaims defines which ResourceClaims must be allocated and reserved before the Pod is allowed to start. The resources will be made available to those containers which consume them by name. This is a stable field but requires that the DynamicResourceAllocation feature gate is enabled. This field is immutable.",
    )
    resources: ResourceRequirements | None = Field(
        default=None,
        alias="resources",
        description='Resources is the total amount of CPU and Memory resources required by all containers in the pod. It supports specifying Requests and Limits for "cpu", "memory" and "hugepages-" resource names only. ResourceClaims are not supported. This field enables fine-grained control over resource allocation for the entire pod, allowing resource sharing among containers in a pod. This is an alpha field and requires enabling the PodLevelResources feature gate.',
    )
    restart_policy: str | None = Field(
        default=None,
        alias="restartPolicy",
        description="Restart policy for all containers within the pod. One of Always, OnFailure, Never. In some contexts, only a subset of those values may be permitted. Default to Always. More info: https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/#restart-policy",
    )
    runtime_class_name: str | None = Field(
        default=None,
        alias="runtimeClassName",
        description='RuntimeClassName refers to a RuntimeClass object in the node.k8s.io group, which should be used to run this pod. If no RuntimeClass resource matches the named class, the pod will not be run. If unset or empty, the "legacy" RuntimeClass will be used, which is an implicit class with an empty definition that uses the default runtime handler. More info: https://git.k8s.io/enhancements/keps/sig-node/585-runtime-class',
    )
    scheduler_name: str | None = Field(
        default=None,
        alias="schedulerName",
        description="If specified, the pod will be dispatched by specified scheduler. If not specified, the pod will be dispatched by default scheduler.",
    )
    scheduling_gates: list[PodSchedulingGate] | None = Field(
        default=None,
        alias="schedulingGates",
        description="SchedulingGates is an opaque list of values that if specified will block scheduling the pod. If schedulingGates is not empty, the pod will stay in the SchedulingGated state and the scheduler will not attempt to schedule the pod. SchedulingGates can only be set at pod creation time, and be removed only afterwards.",
    )
    scheduling_group: PodSchedulingGroup | None = Field(
        default=None,
        alias="schedulingGroup",
        description="SchedulingGroup provides a reference to the immediate scheduling runtime grouping object that this Pod belongs to. This field is used by the scheduler to identify the group and apply the correct group scheduling policies. The association with a group also impacts other lifecycle aspects of a Pod that are relevant in a wider context of scheduling like preemption, resource attachment, etc. If not specified, the Pod is treated as a single unit in all of these aspects. The group object referenced by this field may not exist at the time the Pod is created. This field is immutable, but a group object with the same name may be recreated with different policies. Doing this during pod scheduling may result in the placement not conforming to the expected policies.",
    )
    security_context: PodSecurityContext | None = Field(
        default=None,
        alias="securityContext",
        description="SecurityContext holds pod-level security attributes and common container settings. Optional: Defaults to empty. See type description for default values of each field.",
    )
    service_account: str | None = Field(
        default=None,
        alias="serviceAccount",
        description="DeprecatedServiceAccount is a deprecated alias for ServiceAccountName. Deprecated: Use serviceAccountName instead.",
    )
    service_account_name: str | None = Field(
        default=None,
        alias="serviceAccountName",
        description="ServiceAccountName is the name of the ServiceAccount to use to run this pod. More info: https://kubernetes.io/docs/tasks/configure-pod-container/configure-service-account/",
    )
    set_hostname_as_fqdn: bool | None = Field(
        default=None,
        alias="setHostnameAsFQDN",
        description="If true the pod's hostname will be configured as the pod's FQDN, rather than the leaf name (the default). In Linux containers, this means setting the FQDN in the hostname field of the kernel (the nodename field of struct utsname). In Windows containers, this means setting the registry value of hostname for the registry key HKEY_LOCAL_MACHINE\\\\SYSTEM\\\\CurrentControlSet\\\\Services\\\\Tcpip\\\\Parameters to FQDN. If a pod does not have FQDN, this has no effect. Default to false.",
    )
    share_process_namespace: bool | None = Field(
        default=None,
        alias="shareProcessNamespace",
        description="Share a single process namespace between all of the containers in a pod. When this is set containers will be able to view and signal processes from other containers in the same pod, and the first process in each container will not be assigned PID 1. HostPID and ShareProcessNamespace cannot both be set. Optional: Default to false.",
    )
    subdomain: str | None = Field(
        default=None,
        alias="subdomain",
        description='If specified, the fully qualified Pod hostname will be "<hostname>.<subdomain>.<pod namespace>.svc.<cluster domain>". If not specified, the pod will not have a domainname at all.',
    )
    termination_grace_period_seconds: int | None = Field(
        default=None,
        alias="terminationGracePeriodSeconds",
        description="Optional duration in seconds the pod needs to terminate gracefully. May be decreased in delete request. Value must be non-negative integer. The value zero indicates stop immediately via the kill signal (no opportunity to shut down). If this value is nil, the default grace period will be used instead. The grace period is the duration in seconds after the processes running in the pod are sent a termination signal and the time when the processes are forcibly halted with a kill signal. Set this value longer than the expected cleanup time for your process. Defaults to 30 seconds.",
    )
    tolerations: list[Toleration] | None = Field(
        default=None,
        alias="tolerations",
        description="If specified, the pod's tolerations.",
    )
    topology_spread_constraints: list[TopologySpreadConstraint] | None = Field(
        default=None,
        alias="topologySpreadConstraints",
        description="TopologySpreadConstraints describes how a group of pods ought to spread across topology domains. Scheduler will schedule pods in a way which abides by the constraints. All topologySpreadConstraints are ANDed.",
    )
    volumes: list[Volume] | None = Field(
        default=None,
        alias="volumes",
        description="List of volumes that can be mounted by containers belonging to the pod. More info: https://kubernetes.io/docs/concepts/storage/volumes",
    )
