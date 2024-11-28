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
from kubex.models.list_entity import ListEntity
from kubex.models.resource_config import Scope
from kubex.models.status import Status
from kubex.models.typing import (
    ResourceType,
)
from kubex.models.watch_event import WatchEvent

from ._logs import LogsMixin
from ._metadata import MetadataMixin
from ._protocol import ApiNamespaceTypes


class Api(Generic[ResourceType], MetadataMixin[ResourceType], LogsMixin[ResourceType]):
    """API for interacting with Kubernetes resource."""

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
        self._ensure_optional_namespace(namespace)

    def _get_namespace(self, namespace: ApiNamespaceTypes) -> NamespaceTypes:
        """Get the namespace to use for the API request.

        If the namespace is not provided, the namespace provided when creating
        the API will be used. If the namespace is provided, the namespace
        provided when creating the API will be overridden.
        """
        if namespace is Ellipsis:
            return self._namespace
        return namespace

    def _ensure_required_namespace(
        self, namespace: ApiNamespaceTypes
    ) -> NamespaceTypes:
        _namespace = self._get_namespace(namespace)
        if (
            _namespace is None
            and self._resource.__RESOURCE_CONFIG__.scope == Scope.NAMESPACE
        ):
            raise ValueError("Namespace is required")
        if (
            _namespace is not None
            and self._resource.__RESOURCE_CONFIG__.scope == Scope.CLUSTER
        ):
            raise ValueError("Namespace is not supported for cluster-scoped resources")
        return _namespace

    def _ensure_optional_namespace(
        self, namespace: ApiNamespaceTypes
    ) -> NamespaceTypes:
        _namespace = self._get_namespace(namespace)
        if (
            self._resource.__RESOURCE_CONFIG__.scope == Scope.CLUSTER
            and _namespace is not None
        ):
            raise ValueError("Namespace is not supported for cluster-scoped resources")
        return _namespace

    async def get(
        self,
        name: str,
        *,
        namespace: ApiNamespaceTypes = Ellipsis,
        resource_version: ResourceVersionTypes = None,
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
        Returns:
            ResourceType: the resource instance.
        """
        _namespace = self._ensure_required_namespace(namespace)
        options = GetOptions(resource_version=resource_version)
        request = self._request_builder.get(name, _namespace, options)
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
            timeout: Timeout for the list/watch call.
            limit: The maximum number of items to return.
            continue_token: The continue token for the list call.
            version_match: Whether to watch for changes to a resource.
            resource_version: The resource version to list. If not provided,
                the current resource version will be listed. For details look at
                [Resource Version Semantics documentation](https://kubernetes.io/docs/reference/using-api/api-concepts/#semantics-for-get-and-list),
        Returns:
            ListEntity[ResourceType]: the list of resource.
        """
        _namespace = self._ensure_optional_namespace(namespace)
        options = ListOptions(
            label_selector=label_selector,
            field_selector=field_selector,
            timeout=timeout,
            limit=limit,
            continue_token=continue_token,
            version_match=version_match,
            resource_version=resource_version,
        )
        request = self._request_builder.list(_namespace, options)
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
        Returns:
            ResourceType: the created resource instance.
        """
        _namespace = self._ensure_required_namespace(namespace)
        options = PostOptions(dry_run=dry_run, field_manager=field_manager)
        request = self._request_builder.create(
            _namespace,
            options,
            data.model_dump_json(by_alias=True, exclude_unset=True, exclude_none=True),
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
        Returns:
            Status: the resource has been fully deleted.
            ResourceType: the resource instance deletion process has started,
                but the resource is not gone yet due to finalization process.
                For details see
                [Resource deletion documentation](https://kubernetes.io/docs/reference/using-api/api-concepts/#resource-deletion).
        """
        _namespace = self._ensure_required_namespace(namespace)
        options = DeleteOptions(
            dry_run=dry_run,
            grace_period_seconds=grace_period_seconds,
            propagation_policy=propagation_policy,
            preconditions=preconditions,
        )
        request = self._request_builder.delete(name, _namespace, options)
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
        delete_options: DeleteOptions | None = None,
        dry_run: DryRunTypes = None,
        grace_period_seconds: int | None = None,
        propagation_policy: PropagationPolicyTypes = None,
        preconditions: Precondition | None = None,
    ) -> Status | ListEntity[ResourceType]:
        """Delete collection of resources."""
        _namespace = self._ensure_optional_namespace(namespace)
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
            _namespace, list_options, delete_options
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
    ) -> ResourceType:
        """Patch the specified resource."""
        _namespace = self._ensure_required_namespace(namespace)
        options = PatchOptions(
            dry_run=dry_run,
            field_manager=field_manager,
            force=force,
            field_validation=field_validation,
        )
        request = self._request_builder.patch(name, _namespace, options, patch)
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
    ) -> ResourceType:
        """Replace the specified resource."""
        _namespace = self._ensure_required_namespace(namespace)
        options = PostOptions(dry_run=dry_run, field_manager=field_manager)
        request = self._request_builder.replace(
            name,
            _namespace,
            options,
            data.model_dump_json(by_alias=True, exclude_unset=True, exclude_none=True),
        )
        response = await self._client.request(request)
        return self._resource.model_validate_json(response.content)

    async def watch(
        self,
        *,
        namespace: ApiNamespaceTypes = Ellipsis,
        options: WatchOptions | None = None,
        label_selector: str | None = None,
        field_selector: str | None = None,
        allow_bookmarks: bool | None = None,
        send_initial_events: bool | None = None,
        timeout_seconds: int | None = None,
        resource_version: ResourceVersionTypes = None,
    ) -> AsyncGenerator[WatchEvent[ResourceType], None]:
        """Watch for changes to the specified resource."""
        _namespace = self._ensure_optional_namespace(namespace)
        options = WatchOptions(
            label_selector=label_selector,
            field_selector=field_selector,
            allow_bookmarks=allow_bookmarks,
            send_initial_events=send_initial_events,
            timeout_seconds=timeout_seconds,
        )
        request = self._request_builder.watch(
            _namespace, options, resource_version=resource_version
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
