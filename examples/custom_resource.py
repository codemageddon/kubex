from __future__ import annotations

from typing import ClassVar, Literal

from pydantic import Field

from kubex.api import Api
from kubex.client import create_client
from kubex.core.patch import ApplyPatch
from kubex_core.models.base import BaseK8sModel
from kubex_core.models.interfaces import (
    ClusterScopedEntity,
    HasStatusSubresource,
    NamespaceScopedEntity,
)
from kubex_core.models.metadata import ObjectMetadata
from kubex_core.models.resource_config import ResourceConfig, Scope

NAMESPACE = "default"


class WidgetSpec(BaseK8sModel):
    replicas: int = 1
    image: str = "nginx:latest"


class WidgetStatus(BaseK8sModel):
    ready_replicas: int | None = None


class Widget(NamespaceScopedEntity, HasStatusSubresource):
    """A namespace-scoped custom resource with a status subresource."""

    __RESOURCE_CONFIG__: ClassVar[ResourceConfig["Widget"]] = ResourceConfig(
        version="v1alpha1",
        kind="Widget",
        group="example.io",
        plural="widgets",
        scope=Scope.NAMESPACE,
    )
    api_version: Literal["example.io/v1alpha1"] = Field(
        default="example.io/v1alpha1",
        alias="apiVersion",
    )
    kind: Literal["Widget"] = Field(default="Widget")
    spec: WidgetSpec | None = None
    status: WidgetStatus | None = None


class ClusterWidgetSpec(BaseK8sModel):
    description: str = ""


class ClusterWidget(ClusterScopedEntity):
    """A cluster-scoped custom resource."""

    __RESOURCE_CONFIG__: ClassVar[ResourceConfig["ClusterWidget"]] = ResourceConfig(
        version="v1alpha1",
        kind="ClusterWidget",
        group="example.io",
        plural="clusterwidgets",
        scope=Scope.CLUSTER,
    )
    api_version: Literal["example.io/v1alpha1"] = Field(
        default="example.io/v1alpha1",
        alias="apiVersion",
    )
    kind: Literal["ClusterWidget"] = Field(default="ClusterWidget")
    spec: ClusterWidgetSpec | None = None


async def main() -> None:
    client = await create_client()
    async with client:
        api: Api[Widget] = Api(Widget, client=client, namespace=NAMESPACE)

        widget = await api.create(
            Widget(
                metadata=ObjectMetadata(name="my-widget"),
                spec=WidgetSpec(replicas=2),
            ),
        )
        assert widget.metadata.name is not None
        name = widget.metadata.name

        try:
            fetched = await api.get(name)
            print(
                f"Got widget: {fetched.metadata.name}, replicas={fetched.spec and fetched.spec.replicas}"
            )

            widget_list = await api.list()
            print(f"Listed {len(widget_list.items)} widget(s)")

            patched = await api.patch(
                name,
                ApplyPatch(
                    Widget(
                        api_version="example.io/v1alpha1",
                        kind="Widget",
                        metadata=ObjectMetadata(name=name),
                        spec=WidgetSpec(replicas=3),
                    )
                ),
                field_manager="kubex-example",
                force=True,
            )
            print(f"Patched widget: replicas={patched.spec and patched.spec.replicas}")

            status = await api.status.get(name)
            print(
                f"Status: ready_replicas={status.status and status.status.ready_replicas}"
            )
        finally:
            await api.delete(name)
            print("Deleted widget")

        cluster_api: Api[ClusterWidget] = Api(ClusterWidget, client=client)
        cluster_widget = await cluster_api.create(
            ClusterWidget(
                metadata=ObjectMetadata(name="my-cluster-widget"),
                spec=ClusterWidgetSpec(description="a cluster-wide widget"),
            ),
        )
        assert cluster_widget.metadata.name is not None
        try:
            print(f"Got cluster widget: {cluster_widget.metadata.name}")
        finally:
            await cluster_api.delete(cluster_widget.metadata.name)
            print("Deleted cluster widget")


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
