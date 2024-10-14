from __future__ import annotations
from typing import Any, ClassVar, Literal

from kubex.models.base import (
    ClusterScopedEntity,
    HasStatusSubresource,
    ResourceConfig,
    Scope,
)


class Namespace(ClusterScopedEntity, HasStatusSubresource):
    __RESOURCE_CONFIG__: ClassVar[ResourceConfig[Namespace]] = ResourceConfig[
        "Namespace"
    ](
        version="v1",
        kind="Namespace",
        group="core",
        plural="namespaces",
        scope=Scope.CLUSTER,
    )

    api_version: Literal["v1"] | None = "v1"
    kind: Literal["Namespace"] | None = "Namespace"
    spec: dict[str, Any] | None = None
    status: dict[str, Any] | None = None


b'{"kind":"NamespaceList","apiVersion":"v1","metadata":{"resourceVersion":"56886"},"items":[{"metadata":{"name":"default","uid":"97a2d6d8-3683-4bf7-bb6c-67dddcd2e4ef","resourceVersion":"36","creationTimestamp":"2024-10-09T22:08:00Z","labels":{"kubernetes.io/metadata.name":"default"},"managedFields":[{"manager":"kube-apiserver","operation":"Update","apiVersion":"v1","time":"2024-10-09T22:08:00Z","fieldsType":"FieldsV1","fieldsV1":{"f:metadata":{"f:labels":{".":{},"f:kubernetes.io/metadata.name":{}}}}}]},"spec":{"finalizers":["kubernetes"]},"status":{"phase":"Active"}},{"metadata":{"name":"kube-node-lease","uid":"64889cb3-4543-45c0-a1d1-740cc430e976","resourceVersion":"31","creationTimestamp":"2024-10-09T22:08:00Z","labels":{"kubernetes.io/metadata.name":"kube-node-lease"},"managedFields":[{"manager":"kube-apiserver","operation":"Update","apiVersion":"v1","time":"2024-10-09T22:08:00Z","fieldsType":"FieldsV1","fieldsV1":{"f:metadata":{"f:labels":{".":{},"f:kubernetes.io/metadata.name":{}}}}}]},"spec":{"finalizers":["kubernetes"]},"status":{"phase":"Active"}},{"metadata":{"name":"kube-public","uid":"e62c601b-6188-4602-8e4e-9152bacc77e0","resourceVersion":"17","creationTimestamp":"2024-10-09T22:08:00Z","labels":{"kubernetes.io/metadata.name":"kube-public"},"managedFields":[{"manager":"kube-apiserver","operation":"Update","apiVersion":"v1","time":"2024-10-09T22:08:00Z","fieldsType":"FieldsV1","fieldsV1":{"f:metadata":{"f:labels":{".":{},"f:kubernetes.io/metadata.name":{}}}}}]},"spec":{"finalizers":["kubernetes"]},"status":{"phase":"Active"}},{"metadata":{"name":"kube-system","uid":"a6504480-266e-4aae-973e-fa83eba1d8a0","resourceVersion":"10","creationTimestamp":"2024-10-09T22:08:00Z","labels":{"kubernetes.io/metadata.name":"kube-system"},"managedFields":[{"manager":"kube-apiserver","operation":"Update","apiVersion":"v1","time":"2024-10-09T22:08:00Z","fieldsType":"FieldsV1","fieldsV1":{"f:metadata":{"f:labels":{".":{},"f:kubernetes.io/metadata.name":{}}}}}]},"spec":{"finalizers":["kubernetes"]},"status":{"phase":"Active"}},{"metadata":{"name":"test-c4bst","generateName":"test-","uid":"d31f046f-2322-4103-8ed3-23b106a70b4d","resourceVersion":"26382","creationTimestamp":"2024-10-10T20:34:24Z","labels":{"kubernetes.io/metadata.name":"test-c4bst"},"managedFields":[{"manager":"kubectl-create","operation":"Update","apiVersion":"v1","time":"2024-10-10T20:34:24Z","fieldsType":"FieldsV1","fieldsV1":{"f:metadata":{"f:generateName":{}}}}]},"spec":{"finalizers":["kubernetes"]},"status":{"phase":"Active"}}]}\n'
