from __future__ import annotations

import json
from typing import (
    AsyncGenerator,
    Generic,
    Type,
)

from pydantic import ValidationError

from kubex.client.client import BaseClient, create_client
from kubex.core.params import (
    DeleteOptions,
    DryRunTypes,
    FieldValidation,
    GetOptions,
    ListOptions,
    NamespaceTypes,
    PatchOptions,
    PostOptions,
    Precondition,
    PropagationPolicyTypes,
    ResourceVersionTypes,
    VersionMatch,
    WatchOptions,
)
from kubex.core.patch import Patch
from kubex.core.request_builder.builder import RequestBuilder
from kubex_core.models.list_entity import ListEntity
from kubex_core.models.status import Status
from kubex_core.models.typing import (
    ResourceType,
)
from kubex_core.models.watch_event import WatchEvent

from ._attach import _AttachDescriptor
from ._ephemeral_containers import _EphemeralContainersDescriptor
from ._exec import _ExecDescriptor
from ._eviction import _EvictionDescriptor
from ._logs import _LogsDescriptor
from ._metadata import MetadataAccessor
from ._portforward import _PortforwardDescriptor
from ._resize import _ResizeDescriptor
from ._scale import _ScaleDescriptor
from ._status import _StatusDescriptor
from ._protocol import (
    ApiNamespaceTypes,
    ApiRequestTimeoutTypes,
    ensure_optional_namespace,
    ensure_required_namespace,
)


class Api(Generic[ResourceType]):
    """API for interacting with Kubernetes resource."""

    attach = _AttachDescriptor()
    logs = _LogsDescriptor()
    portforward = _PortforwardDescriptor()
    scale = _ScaleDescriptor()
    status = _StatusDescriptor()
    eviction = _EvictionDescriptor()
    ephemeral_containers = _EphemeralContainersDescriptor()
    resize = _ResizeDescriptor()
    exec = _ExecDescriptor()
    metadata: MetadataAccessor[ResourceType]

    def __init__(
        self,
        resource_type: Type[ResourceType],
        client: BaseClient,
        *,
        namespace: NamespaceTypes = None,
    ) -> None:
        self._resource = resource_type
        self._client = client
        self._request_builder = RequestBuilder(
            resource_config=resource_type.__RESOURCE_CONFIG__,
        )
        self._namespace = namespace
        ensure_optional_namespace(
            namespace, self._namespace, self._resource.__RESOURCE_CONFIG__.scope
        )
        self.metadata = MetadataAccessor(
            client=self._client,
            request_builder=self._request_builder,
            namespace=self._namespace,
            scope=self._resource.__RESOURCE_CONFIG__.scope,
            resource_type=self._resource,
        )

    async def get(
        self,
        name: str,
        *,
        namespace: ApiNamespaceTypes = Ellipsis,
        resource_version: ResourceVersionTypes = None,
        request_timeout: ApiRequestTimeoutTypes = Ellipsis,
    ) -> ResourceType:
        """Read the specified resource.

        Args:
            name: The name of the resource to read.
            namespace: The namespace of the namespaced resource to read. If not provided,
                the namespace provided when creating the API will be used.
                The namespace is required for namespaced resources.
                If namespace is provided for cluster-scoped resources, an error will be raised.
            resource_version: The resource version to read. If not provided,
                the current resource version will be read. For details look at
                [Resource Version Semantics documentation](https://kubernetes.io/docs/reference/using-api/api-concepts/#semantics-for-get-and-list),
            request_timeout: HTTP-level timeout override for this call. A number is
                interpreted as the total timeout in seconds. Pass ``None`` to disable
                timeouts entirely for this call. Omit to use the client default.
        Returns:
            ResourceType: the resource instance.
        """
        _namespace = ensure_required_namespace(
            namespace, self._namespace, self._resource.__RESOURCE_CONFIG__.scope
        )
        options = GetOptions(resource_version=resource_version)
        request = self._request_builder.get(
            name, _namespace, options, request_timeout=request_timeout
        )
        response = await self._client.request(request)
        return self._resource.model_validate_json(response.content)

    async def list(
        self,
        *,
        namespace: ApiNamespaceTypes = Ellipsis,
        label_selector: str | None = None,
        field_selector: str | None = None,
        timeout: int | None = None,
        limit: int | None = None,
        continue_token: str | None = None,
        version_match: VersionMatch | None = None,
        resource_version: ResourceVersionTypes = None,
        request_timeout: ApiRequestTimeoutTypes = Ellipsis,
    ) -> ListEntity[ResourceType]:
        """List objects of kind.

        Args:
            namespace: The namespace of the namespaced resource to list. If not provided,
                the namespace provided when creating the API will be used.
                If namespace is provided for cluster-scoped resources, an error will be raised.
            label_selector: A selector to restrict the list of returned objects by their labels.
                For details look at [Label Selectors documentation](https://kubernetes.io/docs/concepts/overview/working-with-objects/labels/#label-selectors).
            field_selector: A selector to restrict the list of returned objects by their fields.
                For details look at [Field Selectors documentation](https://kubernetes.io/docs/concepts/overview/working-with-objects/field-selectors/).
            timeout: Server-side timeout (in seconds) for the list/watch call;
                sent as the Kubernetes ``timeoutSeconds`` query parameter. For an
                HTTP client-side timeout, use ``request_timeout``.
            limit: The maximum number of items to return.
            continue_token: The continue token for the list call.
            version_match: Whether to watch for changes to a resource.
            resource_version: The resource version to list. If not provided,
                the current resource version will be listed. For details look at
                [Resource Version Semantics documentation](https://kubernetes.io/docs/reference/using-api/api-concepts/#semantics-for-get-and-list),
            request_timeout: HTTP-level timeout override for this call. A number is
                interpreted as the total timeout in seconds. Pass ``None`` to disable
                timeouts entirely for this call. Omit to use the client default.
        Returns:
            ListEntity[ResourceType]: the list of resource.
        """
        _namespace = ensure_optional_namespace(
            namespace, self._namespace, self._resource.__RESOURCE_CONFIG__.scope
        )
        options = ListOptions(
            label_selector=label_selector,
            field_selector=field_selector,
            timeout=timeout,
            limit=limit,
            continue_token=continue_token,
            version_match=version_match,
            resource_version=resource_version,
        )
        request = self._request_builder.list(
            _namespace, options, request_timeout=request_timeout
        )
        response = await self._client.request(request)
        list_model = self._resource.__RESOURCE_CONFIG__.list_model
        return list_model.model_validate_json(response.content)

    async def create(
        self,
        data: ResourceType,
        *,
        namespace: ApiNamespaceTypes = Ellipsis,
        dry_run: DryRunTypes = None,
        field_manager: str | None = None,
        request_timeout: ApiRequestTimeoutTypes = Ellipsis,
    ) -> ResourceType:
        """Create a resource.

        Args:
            data (ResourceType): The resource instance to create.
            namespace: The namespace to create the resource in. If not provided,
                the namespace provided when creating the API will be used.
                The namespace is required for namespaced resources.
                If namespace is provided for cluster-scoped resources, an error will be raised.
            dry_run: Whether to perform a dry run of the operation.
            field_manager (str): The value to use for the fieldManager attribute of the created resource.
            request_timeout: HTTP-level timeout override for this call. A number is
                interpreted as the total timeout in seconds. Pass ``None`` to disable
                timeouts entirely for this call. Omit to use the client default.
        Returns:
            ResourceType: the created resource instance.
        """
        _namespace = ensure_required_namespace(
            namespace, self._namespace, self._resource.__RESOURCE_CONFIG__.scope
        )
        options = PostOptions(dry_run=dry_run, field_manager=field_manager)
        request = self._request_builder.create(
            _namespace,
            options,
            data.model_dump_json(by_alias=True, exclude_unset=True, exclude_none=True),
            request_timeout=request_timeout,
        )
        response = await self._client.request(request)
        return self._resource.model_validate_json(response.content)

    async def delete(
        self,
        name: str,
        *,
        namespace: ApiNamespaceTypes = Ellipsis,
        dry_run: DryRunTypes = None,
        grace_period_seconds: int | None = None,
        propagation_policy: PropagationPolicyTypes = None,
        preconditions: Precondition | None = None,
        request_timeout: ApiRequestTimeoutTypes = Ellipsis,
    ) -> Status | ResourceType:
        """Delete the specified resource.

        Args:
            name: The name of the resource to delete.
            namespace: The namespace of the namespaced resource to delete. If not provided,
                the namespace provided when creating the API will be used.
                The namespace is required for namespaced resources.
                If namespace is provided for cluster-scoped resources, an error will be raised.
            dry_run: Whether to perform a dry run of the operation.
            grace_period_seconds: The duration in seconds before the object should be deleted.
            propagation_policy: Whether and how garbage collection will be performed.
            preconditions: Preconditions for the operation.
            request_timeout: HTTP-level timeout override for this call. A number is
                interpreted as the total timeout in seconds. Pass ``None`` to disable
                timeouts entirely for this call. Omit to use the client default.
        Returns:
            Status: the resource has been fully deleted.
            ResourceType: the resource instance deletion process has started,
                but the resource is not gone yet due to finalization process.
                For details see
                [Resource deletion documentation](https://kubernetes.io/docs/reference/using-api/api-concepts/#resource-deletion).
        """
        _namespace = ensure_required_namespace(
            namespace, self._namespace, self._resource.__RESOURCE_CONFIG__.scope
        )
        options = DeleteOptions(
            dry_run=dry_run,
            grace_period_seconds=grace_period_seconds,
            propagation_policy=propagation_policy,
            preconditions=preconditions,
        )
        request = self._request_builder.delete(
            name, _namespace, options, request_timeout=request_timeout
        )
        response = await self._client.request(request)
        try:
            return Status.model_validate_json(response.content)
        except ValidationError:
            return self._resource.model_validate_json(response.content)

    async def delete_collection(
        self,
        *,
        namespace: ApiNamespaceTypes = Ellipsis,
        label_selector: str | None = None,
        field_selector: str | None = None,
        timeout: int | None = None,
        limit: int | None = None,
        continue_token: str | None = None,
        version_match: VersionMatch | None = None,
        resource_version: ResourceVersionTypes = None,
        dry_run: DryRunTypes = None,
        grace_period_seconds: int | None = None,
        propagation_policy: PropagationPolicyTypes = None,
        preconditions: Precondition | None = None,
        request_timeout: ApiRequestTimeoutTypes = Ellipsis,
    ) -> Status | ListEntity[ResourceType]:
        """Delete collection of resources.

        Args:
            request_timeout: HTTP-level timeout override for this call. A number is
                interpreted as the total timeout in seconds. Pass ``None`` to disable
                timeouts entirely for this call. Omit to use the client default.
        """
        _namespace = ensure_optional_namespace(
            namespace, self._namespace, self._resource.__RESOURCE_CONFIG__.scope
        )
        list_options = ListOptions(
            label_selector=label_selector,
            field_selector=field_selector,
            timeout=timeout,
            limit=limit,
            continue_token=continue_token,
            version_match=version_match,
            resource_version=resource_version,
        )
        delete_options = DeleteOptions(
            dry_run=dry_run,
            grace_period_seconds=grace_period_seconds,
            propagation_policy=propagation_policy,
            preconditions=preconditions,
        )
        request = self._request_builder.delete_collection(
            _namespace,
            list_options,
            delete_options,
            request_timeout=request_timeout,
        )
        response = await self._client.request(request)
        list_model = self._resource.__RESOURCE_CONFIG__.list_model
        try:
            return Status.model_validate_json(response.content)
        except ValidationError:
            return list_model.model_validate_json(response.content)

    async def patch(
        self,
        name: str,
        patch: Patch,
        *,
        namespace: ApiNamespaceTypes = Ellipsis,
        dry_run: DryRunTypes = None,
        field_manager: str | None = None,
        force: bool | None = None,
        field_validation: FieldValidation | None = None,
        request_timeout: ApiRequestTimeoutTypes = Ellipsis,
    ) -> ResourceType:
        """Patch the specified resource.

        Args:
            request_timeout: HTTP-level timeout override for this call. A number is
                interpreted as the total timeout in seconds. Pass ``None`` to disable
                timeouts entirely for this call. Omit to use the client default.
        """
        _namespace = ensure_required_namespace(
            namespace, self._namespace, self._resource.__RESOURCE_CONFIG__.scope
        )
        options = PatchOptions(
            dry_run=dry_run,
            field_manager=field_manager,
            force=force,
            field_validation=field_validation,
        )
        request = self._request_builder.patch(
            name, _namespace, options, patch, request_timeout=request_timeout
        )
        response = await self._client.request(request)
        return self._resource.model_validate_json(response.content)

    async def replace(
        self,
        name: str,
        data: ResourceType,
        *,
        namespace: ApiNamespaceTypes = Ellipsis,
        dry_run: DryRunTypes = None,
        field_manager: str | None = None,
        request_timeout: ApiRequestTimeoutTypes = Ellipsis,
    ) -> ResourceType:
        """Replace the specified resource.

        Args:
            request_timeout: HTTP-level timeout override for this call. A number is
                interpreted as the total timeout in seconds. Pass ``None`` to disable
                timeouts entirely for this call. Omit to use the client default.
        """
        _namespace = ensure_required_namespace(
            namespace, self._namespace, self._resource.__RESOURCE_CONFIG__.scope
        )
        options = PostOptions(dry_run=dry_run, field_manager=field_manager)
        request = self._request_builder.replace(
            name,
            _namespace,
            options,
            data.model_dump_json(by_alias=True, exclude_unset=True, exclude_none=True),
            request_timeout=request_timeout,
        )
        response = await self._client.request(request)
        return self._resource.model_validate_json(response.content)

    async def watch(
        self,
        *,
        namespace: ApiNamespaceTypes = Ellipsis,
        label_selector: str | None = None,
        field_selector: str | None = None,
        allow_bookmarks: bool | None = None,
        send_initial_events: bool | None = None,
        timeout_seconds: int | None = None,
        resource_version: ResourceVersionTypes = None,
        request_timeout: ApiRequestTimeoutTypes = Ellipsis,
    ) -> AsyncGenerator[WatchEvent[ResourceType], None]:
        """Watch for changes to the specified resource.

        Args:
            request_timeout: HTTP-level timeout override for this call. A number is
                interpreted as the total timeout in seconds. Pass ``None`` to disable
                timeouts entirely for this call. Omit to use the client default. For
                long-lived watches a short read/total timeout will terminate the
                stream; disable the read timeout or leave this unset.
        """
        _namespace = ensure_optional_namespace(
            namespace, self._namespace, self._resource.__RESOURCE_CONFIG__.scope
        )
        options = WatchOptions(
            label_selector=label_selector,
            field_selector=field_selector,
            allow_bookmarks=allow_bookmarks,
            send_initial_events=send_initial_events,
            timeout_seconds=timeout_seconds,
        )
        request = self._request_builder.watch(
            _namespace,
            options,
            resource_version=resource_version,
            request_timeout=request_timeout,
        )
        async for line in self._client.stream_lines(request):
            yield WatchEvent(self._resource, json.loads(line))


async def create_api(
    resource_type: Type[ResourceType],
    *,
    client: BaseClient | None = None,
    namespace: NamespaceTypes = None,
) -> Api[ResourceType]:
    """Create an API for the specified resource type.

    Args:
        resource_type: The resource type to create an API for.
        client: The client to use for the API. If not provided,
            a new client will be created.
        namespace: The namespace to use for the API. If set all
            operations will be performed in this namespace.
            The Api namespace can be overridden by passing a
            namespace to the individual methods.
    Returns:
        An Api instance for the specified resource type.
    """
    client = client or await create_client()
    return Api(resource_type, client=client, namespace=namespace)
