from pydantic import Field

from kubex.k8s.v1_33.core.v1.container_port import ContainerPort
from kubex.k8s.v1_33.core.v1.container_resize_policy import ContainerResizePolicy
from kubex.k8s.v1_33.core.v1.env_from_source import EnvFromSource
from kubex.k8s.v1_33.core.v1.env_var import EnvVar
from kubex.k8s.v1_33.core.v1.lifecycle import Lifecycle
from kubex.k8s.v1_33.core.v1.probe import Probe
from kubex.k8s.v1_33.core.v1.resource_requirements import ResourceRequirements
from kubex.k8s.v1_33.core.v1.security_context import SecurityContext
from kubex.k8s.v1_33.core.v1.volume_device import VolumeDevice
from kubex.k8s.v1_33.core.v1.volume_mount import VolumeMount
from kubex_core.models.base import BaseK8sModel


class EphemeralContainer(BaseK8sModel):
    """An EphemeralContainer is a temporary container that you may add to an existing Pod for user-initiated activities such as debugging. Ephemeral containers have no resource or scheduling guarantees, and they will not be restarted when they exit or when a Pod is removed or restarted. The kubelet may evict a Pod if an ephemeral container causes the Pod to exceed its resource allocation. To add an ephemeral container, use the ephemeralcontainers subresource of an existing Pod. Ephemeral containers may not be removed or restarted."""

    args: list[str] | None = Field(
        default=None,
        alias="args",
        description='Arguments to the entrypoint. The image\'s CMD is used if this is not provided. Variable references $(VAR_NAME) are expanded using the container\'s environment. If a variable cannot be resolved, the reference in the input string will be unchanged. Double $$ are reduced to a single $, which allows for escaping the $(VAR_NAME) syntax: i.e. "$$(VAR_NAME)" will produce the string literal "$(VAR_NAME)". Escaped references will never be expanded, regardless of whether the variable exists or not. Cannot be updated. More info: https://kubernetes.io/docs/tasks/inject-data-application/define-command-argument-container/#running-a-command-in-a-shell',
    )
    command: list[str] | None = Field(
        default=None,
        alias="command",
        description='Entrypoint array. Not executed within a shell. The image\'s ENTRYPOINT is used if this is not provided. Variable references $(VAR_NAME) are expanded using the container\'s environment. If a variable cannot be resolved, the reference in the input string will be unchanged. Double $$ are reduced to a single $, which allows for escaping the $(VAR_NAME) syntax: i.e. "$$(VAR_NAME)" will produce the string literal "$(VAR_NAME)". Escaped references will never be expanded, regardless of whether the variable exists or not. Cannot be updated. More info: https://kubernetes.io/docs/tasks/inject-data-application/define-command-argument-container/#running-a-command-in-a-shell',
    )
    env: list[EnvVar] | None = Field(
        default=None,
        alias="env",
        description="List of environment variables to set in the container. Cannot be updated.",
    )
    env_from: list[EnvFromSource] | None = Field(
        default=None,
        alias="envFrom",
        description="List of sources to populate environment variables in the container. The keys defined within a source must be a C_IDENTIFIER. All invalid keys will be reported as an event when the container is starting. When a key exists in multiple sources, the value associated with the last source will take precedence. Values defined by an Env with a duplicate key will take precedence. Cannot be updated.",
    )
    image: str | None = Field(
        default=None,
        alias="image",
        description="Container image name. More info: https://kubernetes.io/docs/concepts/containers/images",
    )
    image_pull_policy: str | None = Field(
        default=None,
        alias="imagePullPolicy",
        description="Image pull policy. One of Always, Never, IfNotPresent. Defaults to Always if :latest tag is specified, or IfNotPresent otherwise. Cannot be updated. More info: https://kubernetes.io/docs/concepts/containers/images#updating-images",
    )
    lifecycle: Lifecycle | None = Field(
        default=None,
        alias="lifecycle",
        description="Lifecycle is not allowed for ephemeral containers.",
    )
    liveness_probe: Probe | None = Field(
        default=None,
        alias="livenessProbe",
        description="Probes are not allowed for ephemeral containers.",
    )
    name: str = Field(
        ...,
        alias="name",
        description="Name of the ephemeral container specified as a DNS_LABEL. This name must be unique among all containers, init containers and ephemeral containers.",
    )
    ports: list[ContainerPort] | None = Field(
        default=None,
        alias="ports",
        description="Ports are not allowed for ephemeral containers.",
    )
    readiness_probe: Probe | None = Field(
        default=None,
        alias="readinessProbe",
        description="Probes are not allowed for ephemeral containers.",
    )
    resize_policy: list[ContainerResizePolicy] | None = Field(
        default=None,
        alias="resizePolicy",
        description="Resources resize policy for the container.",
    )
    resources: ResourceRequirements | None = Field(
        default=None,
        alias="resources",
        description="Resources are not allowed for ephemeral containers. Ephemeral containers use spare resources already allocated to the pod.",
    )
    restart_policy: str | None = Field(
        default=None,
        alias="restartPolicy",
        description="Restart policy for the container to manage the restart behavior of each container within a pod. This may only be set for init containers. You cannot set this field on ephemeral containers.",
    )
    security_context: SecurityContext | None = Field(
        default=None,
        alias="securityContext",
        description="Optional: SecurityContext defines the security options the ephemeral container should be run with. If set, the fields of SecurityContext override the equivalent fields of PodSecurityContext.",
    )
    startup_probe: Probe | None = Field(
        default=None,
        alias="startupProbe",
        description="Probes are not allowed for ephemeral containers.",
    )
    stdin: bool | None = Field(
        default=None,
        alias="stdin",
        description="Whether this container should allocate a buffer for stdin in the container runtime. If this is not set, reads from stdin in the container will always result in EOF. Default is false.",
    )
    stdin_once: bool | None = Field(
        default=None,
        alias="stdinOnce",
        description="Whether the container runtime should close the stdin channel after it has been opened by a single attach. When stdin is true the stdin stream will remain open across multiple attach sessions. If stdinOnce is set to true, stdin is opened on container start, is empty until the first client attaches to stdin, and then remains open and accepts data until the client disconnects, at which time stdin is closed and remains closed until the container is restarted. If this flag is false, a container processes that reads from stdin will never receive an EOF. Default is false",
    )
    target_container_name: str | None = Field(
        default=None,
        alias="targetContainerName",
        description="If set, the name of the container from PodSpec that this ephemeral container targets. The ephemeral container will be run in the namespaces (IPC, PID, etc) of this container. If not set then the ephemeral container uses the namespaces configured in the Pod spec. The container runtime must implement support for this feature. If the runtime does not support namespace targeting then the result of setting this field is undefined.",
    )
    termination_message_path: str | None = Field(
        default=None,
        alias="terminationMessagePath",
        description="Optional: Path at which the file to which the container's termination message will be written is mounted into the container's filesystem. Message written is intended to be brief final status, such as an assertion failure message. Will be truncated by the node if greater than 4096 bytes. The total message length across all containers will be limited to 12kb. Defaults to /dev/termination-log. Cannot be updated.",
    )
    termination_message_policy: str | None = Field(
        default=None,
        alias="terminationMessagePolicy",
        description="Indicate how the termination message should be populated. File will use the contents of terminationMessagePath to populate the container status message on both success and failure. FallbackToLogsOnError will use the last chunk of container log output if the termination message file is empty and the container exited with an error. The log output is limited to 2048 bytes or 80 lines, whichever is smaller. Defaults to File. Cannot be updated.",
    )
    tty: bool | None = Field(
        default=None,
        alias="tty",
        description="Whether this container should allocate a TTY for itself, also requires 'stdin' to be true. Default is false.",
    )
    volume_devices: list[VolumeDevice] | None = Field(
        default=None,
        alias="volumeDevices",
        description="volumeDevices is the list of block devices to be used by the container.",
    )
    volume_mounts: list[VolumeMount] | None = Field(
        default=None,
        alias="volumeMounts",
        description="Pod volumes to mount into the container's filesystem. Subpath mounts are not allowed for ephemeral containers. Cannot be updated.",
    )
    working_dir: str | None = Field(
        default=None,
        alias="workingDir",
        description="Container's working directory. If not specified, the container runtime's default will be used, which might be configured in the container image. Cannot be updated.",
    )
