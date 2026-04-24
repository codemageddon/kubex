"""Type-level tests for descriptor-based subresource APIs.

Run with: uv run mypy test/test_subresource_descriptors/test_descriptor_typing.py
"""

from __future__ import annotations

from typing import TYPE_CHECKING, assert_type

if TYPE_CHECKING:
    from unittest.mock import MagicMock

    from kubex.api._ephemeral_containers import EphemeralContainersAccessor
    from kubex.api._eviction import EvictionAccessor
    from kubex.api._logs import LogsAccessor
    from kubex.api._protocol import SubresourceNotAvailable
    from kubex.api._resize import ResizeAccessor
    from kubex.api._scale import ScaleAccessor
    from kubex.api._status import StatusAccessor
    from kubex.api.api import Api
    from kubex.k8s.v1_35.apps.v1.deployment import Deployment
    from kubex.k8s.v1_35.core.v1.namespace import Namespace
    from kubex.k8s.v1_35.core.v1.pod import Pod

    client = MagicMock()

    pod_api: Api[Pod] = Api(Pod, client=client)
    deploy_api: Api[Deployment] = Api(Deployment, client=client, namespace="default")
    ns_api: Api[Namespace] = Api(Namespace, client=client)

    # Pod: HasLogs=yes, HasScale=no, HasStatus=yes, Evictable=yes,
    #       HasEphemeralContainers=yes, HasResize=yes
    assert_type(pod_api.logs, LogsAccessor[Pod])
    assert_type(pod_api.scale, SubresourceNotAvailable)
    assert_type(pod_api.status, StatusAccessor[Pod])
    assert_type(pod_api.eviction, EvictionAccessor[Pod])
    assert_type(pod_api.ephemeral_containers, EphemeralContainersAccessor[Pod])
    assert_type(pod_api.resize, ResizeAccessor[Pod])

    # Deployment: HasLogs=no, HasScale=yes, HasStatus=yes, Evictable=no,
    #             HasEphemeralContainers=no, HasResize=no
    assert_type(deploy_api.logs, SubresourceNotAvailable)
    assert_type(deploy_api.scale, ScaleAccessor[Deployment])
    assert_type(deploy_api.status, StatusAccessor[Deployment])
    assert_type(deploy_api.eviction, SubresourceNotAvailable)
    assert_type(deploy_api.ephemeral_containers, SubresourceNotAvailable)
    assert_type(deploy_api.resize, SubresourceNotAvailable)

    # Namespace: HasLogs=no, HasScale=no, HasStatus=yes, Evictable=no,
    #            HasEphemeralContainers=no, HasResize=no
    assert_type(ns_api.logs, SubresourceNotAvailable)
    assert_type(ns_api.scale, SubresourceNotAvailable)
    assert_type(ns_api.status, StatusAccessor[Namespace])
    assert_type(ns_api.eviction, SubresourceNotAvailable)
    assert_type(ns_api.ephemeral_containers, SubresourceNotAvailable)
    assert_type(ns_api.resize, SubresourceNotAvailable)
