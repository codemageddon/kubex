from pydantic import Field

from kubex.k8s.v1_34.core.v1.lifecycle_handler import LifecycleHandler
from kubex_core.models.base import BaseK8sModel


class Lifecycle(BaseK8sModel):
    """Lifecycle describes actions that the management system should take in response to container lifecycle events. For the PostStart and PreStop lifecycle handlers, management of the container blocks until the action is complete, unless the container process fails, in which case the handler is aborted."""

    post_start: LifecycleHandler | None = Field(
        default=None,
        alias="postStart",
        description="PostStart is called immediately after a container is created. If the handler fails, the container is terminated and restarted according to its restart policy. Other management of the container blocks until the hook completes. More info: https://kubernetes.io/docs/concepts/containers/container-lifecycle-hooks/#container-hooks",
    )
    pre_stop: LifecycleHandler | None = Field(
        default=None,
        alias="preStop",
        description="PreStop is called immediately before a container is terminated due to an API request or management event such as liveness/startup probe failure, preemption, resource contention, etc. The handler is not called if the container crashes or exits. The Pod's termination grace period countdown begins before the PreStop hook is executed. Regardless of the outcome of the handler, the container will eventually terminate within the Pod's termination grace period (unless delayed by finalizers). Other management of the container blocks until the hook completes or until the termination grace period is reached. More info: https://kubernetes.io/docs/concepts/containers/container-lifecycle-hooks/#container-hooks",
    )
    stop_signal: str | None = Field(
        default=None,
        alias="stopSignal",
        description="StopSignal defines which signal will be sent to a container when it is being stopped. If not specified, the default is defined by the container runtime in use. StopSignal can only be set for Pods with a non-empty .spec.os.name",
    )
