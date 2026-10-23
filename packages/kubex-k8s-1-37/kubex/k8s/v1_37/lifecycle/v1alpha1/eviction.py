from __future__ import annotations

from typing import ClassVar, Literal

from pydantic import Field

from kubex.k8s.v1_37.lifecycle.v1alpha1.eviction_spec import EvictionSpec
from kubex.k8s.v1_37.lifecycle.v1alpha1.eviction_status import EvictionStatus
from kubex_core.models.interfaces import HasStatusSubresource, NamespaceScopedEntity
from kubex_core.models.resource_config import ResourceConfig, Scope


class Eviction(NamespaceScopedEntity, HasStatusSubresource):
    """Eviction initiates an eviction process, which should ideally result in a graceful eviction of a .spec.target (e.g. termination of a pod). The evictionrequest-controller observes intents of all EvictionRequests and transforms them into Evictions. It manages the Eviction lifecycle. Requesters are preserved in .status.requesters even after they have withdrawn their request. If all requesters withdraw their eviction intent for a common target, the eviction will be canceled. Once all EvictionRequest corresponding to this Eviction .spec.target have been removed, this Eviction object will eventually be garbage collected. If the target is a pod, the .status.targetResponders is populated from Pod's .spec.evictionResponders. Responders should observe and communicate through the .status to help with the eviction of the target when they see their state == Active in .status.targetResponders. ResponderStatus struct should then be periodically updated to indicate the progress or completion of the eviction process by each responder in .status.responders. If .status.responders[].heartbeatTime is not updated within the heartbeat deadline defined by the Eviction API (currently 20 minutes), the eviction is passed over to the next responder with a lower priority. If there are no other responders and the target is a pod, the last default imperative-eviction.k8s.io/evictor responder with a priority of 100 will evict the pod using the imperative Eviction API (pods/<name>/eviction subresource)."""

    __RESOURCE_CONFIG__: ClassVar[ResourceConfig["Eviction"]] = ResourceConfig[
        "Eviction"
    ](
        version="v1alpha1",
        kind="Eviction",
        group="lifecycle.k8s.io",
        plural="evictions",
        scope=Scope.NAMESPACE,
    )
    api_version: Literal["lifecycle.k8s.io/v1alpha1"] = Field(
        default="lifecycle.k8s.io/v1alpha1",
        alias="apiVersion",
        description="APIVersion defines the versioned schema of this representation of an object. Servers should convert recognized schemas to the latest internal value, and may reject unrecognized values. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#resources",
    )
    kind: Literal["Eviction"] = Field(
        default="Eviction",
        alias="kind",
        description="Kind is a string value representing the REST resource this object represents. Servers may infer this from the endpoint the client submits requests to. Cannot be updated. In CamelCase. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds",
    )
    spec: EvictionSpec = Field(
        ...,
        alias="spec",
        description="spec defines the eviction specification. https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#spec-and-status",
    )
    status: EvictionStatus | None = Field(
        default=None,
        alias="status",
        description="status represents the most recently observed status of the eviction. Populated by responders and evictionrequest-controller. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#spec-and-status",
    )
