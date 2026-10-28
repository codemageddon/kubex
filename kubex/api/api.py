from __future__ import annotations

import json
from typing import (
    AsyncGenerator,
    Generic,
    Literal,
    Type,
    overload,
)

from pydantic import ValidationError

from kubex.client.client import BaseClient, create_client
from kubex.core.invalid_object import ListWithInvalid, _validate_list_with_invalid
from kubex.core.params import (
    DeleteOptions,
    DryRunTypes,
    FieldValidationTypes,
    GetOptions,
    InvalidObjects,
    InvalidObjectsTypes,
    ListOptions,
    PatchOptions,
    PostOptions,
    Precondition,
    PropagationPolicyTypes,
    ResourceVersionTypes,
    VersionMatchTypes,
    WatchOptions,
)
from kubex.core.patch import Patch
from kubex.core.request_builder.builder import RequestBuilder
from kubex.core.watch_event import InvalidWatchEvent, WatchEvent, _parse_watch_event
from kubex_core.models.list_entity import ListEntity
from kubex_core.models.resource_config import Scope
from kubex_core.models.status import Status
from kubex_core.models.typing import (
    ResourceType,
)

from ._attach import _AttachDescriptor
from ._ephemeral_containers import _EphemeralContainersDescriptor
from ._eviction import _EvictionDescriptor
from ._exec import _ExecDescriptor
from ._logs import _LogsDescriptor
from ._metadata import MetadataAccessor
from ._portforward import _PortforwardDescriptor
from ._protocol import (
    ApiNamespaceTypes,
    ApiRequestTimeoutTypes,
    ensure_optional_namespace,
    ensure_required_namespace,
)
from ._resize import _ResizeDescriptor
from ._scale import _ScaleDescriptor
from ._status import _StatusDescriptor


class Api(Generic[ResourceType]):
    """API for interacting with a Kubernetes resource type.

    Args:
        resource_type: The resource model class to operate on, e.g. ``Pod``.
        client: The client used to send requests.
        namespace: The default namespace for this API's calls; each method can
            override it. If omitted, a namespace-scoped resource uses the client's
            configured namespace (the kubeconfig context's namespace, or the pod's
            own namespace in-cluster). Pass ``None`` for no default, which means
            "all namespaces" for ``list``, ``watch`` and ``delete_collection``.
            Cluster-scoped resources never get a namespace; passing one for them
            raises ``ValueError``.

    Raises:
        ValueError: ``namespace`` is given for a cluster-scoped resource.
    """

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
        namespace: ApiNamespaceTypes = Ellipsis,
    ) -> None:
        self._resource = resource_type
        self._client = client
        self._request_builder = RequestBuilder(
            resource_config=resource_type.__RESOURCE_CONFIG__,
        )
        scope = self._resource.__RESOURCE_CONFIG__.scope
        if namespace is Ellipsis:
            # Unspecified: seed from the client's configured namespace, but only
            # for namespace-scoped resources -- a cluster-scoped resource must
            # never receive a namespace, configured or not. An explicit `None`
            # (rather than omitting the argument) still means "all namespaces"
            # and is never overridden by the client's configured namespace.
            # An empty configured namespace (e.g. `namespace: ""` in a kubeconfig
            # context) means "not set", not an empty path segment.
            namespace = (
                client.configuration.namespace or None
                if scope == Scope.NAMESPACE
                else None
            )
        self._namespace = namespace
        ensure_optional_namespace(namespace, self._namespace, scope)
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
                [Resource Version Semantics documentation](https://kubernetes.io/docs/reference/using-api/api-concepts/#semantics-for-get-and-list).
            request_timeout: HTTP-level timeout override for this call. A number is
                interpreted as the total timeout in seconds. Pass ``None`` to disable
                timeouts entirely for this call. Omit to use the client default.

        Returns:
            ResourceType: the resource instance.

        Raises:
            ValueError: an argument is invalid, e.g. an empty or malformed ``name``,
                or a namespace that is missing for a namespace-scoped resource or
                given for a cluster-scoped one.
            NotFound: the resource does not exist.
            KubexApiError: the API server rejected the request; the subclass
                matches the HTTP status (e.g. ``Forbidden``, ``UnprocessableEntity``).
            KubexConnectionError: the API server could not be reached.
            KubexTimeoutError: the request timed out on the client side.
            ConfigurationError: credentials could not be obtained, e.g. an exec
                plugin or OIDC token refresh failed.
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

    @overload
    async def list(
        self,
        *,
        namespace: ApiNamespaceTypes = Ellipsis,
        label_selector: str | None = None,
        field_selector: str | None = None,
        timeout_seconds: int | None = None,
        limit: int | None = None,
        continue_token: str | None = None,
        version_match: VersionMatchTypes = None,
        resource_version: ResourceVersionTypes = None,
        request_timeout: ApiRequestTimeoutTypes = Ellipsis,
        invalid: Literal[InvalidObjects.RAISE, "raise"] = InvalidObjects.RAISE,
    ) -> ListEntity[ResourceType]: ...

    @overload
    async def list(
        self,
        *,
        namespace: ApiNamespaceTypes = Ellipsis,
        label_selector: str | None = None,
        field_selector: str | None = None,
        timeout_seconds: int | None = None,
        limit: int | None = None,
        continue_token: str | None = None,
        version_match: VersionMatchTypes = None,
        resource_version: ResourceVersionTypes = None,
        request_timeout: ApiRequestTimeoutTypes = Ellipsis,
        invalid: Literal[InvalidObjects.INCLUDE, "include"],
    ) -> ListWithInvalid[ResourceType]: ...

    @overload
    async def list(
        self,
        *,
        namespace: ApiNamespaceTypes = Ellipsis,
        label_selector: str | None = None,
        field_selector: str | None = None,
        timeout_seconds: int | None = None,
        limit: int | None = None,
        continue_token: str | None = None,
        version_match: VersionMatchTypes = None,
        resource_version: ResourceVersionTypes = None,
        request_timeout: ApiRequestTimeoutTypes = Ellipsis,
        invalid: InvalidObjectsTypes,
    ) -> ListEntity[ResourceType]: ...

    async def list(
        self,
        *,
        namespace: ApiNamespaceTypes = Ellipsis,
        label_selector: str | None = None,
        field_selector: str | None = None,
        timeout_seconds: int | None = None,
        limit: int | None = None,
        continue_token: str | None = None,
        version_match: VersionMatchTypes = None,
        resource_version: ResourceVersionTypes = None,
        request_timeout: ApiRequestTimeoutTypes = Ellipsis,
        invalid: InvalidObjectsTypes = InvalidObjects.RAISE,
    ) -> ListEntity[ResourceType]:
        """List objects of kind.

        Args:
            namespace: The namespace of the namespaced resource to list. If not provided,
                the namespace provided when creating the API will be used.
                Pass ``None`` to list across all namespaces.
                If namespace is provided for cluster-scoped resources, an error will be raised.
            label_selector: A selector to restrict the list of returned objects by their labels.
                For details look at [Label Selectors documentation](https://kubernetes.io/docs/concepts/overview/working-with-objects/labels/#label-selectors).
            field_selector: A selector to restrict the list of returned objects by their fields.
                For details look at [Field Selectors documentation](https://kubernetes.io/docs/concepts/overview/working-with-objects/field-selectors/).
            timeout_seconds: Server-side timeout (in seconds) for the list/watch call;
                sent as the Kubernetes ``timeoutSeconds`` query parameter. For an
                HTTP client-side timeout, use ``request_timeout``.
            limit: The maximum number of items to return. If more items match, the
                returned list's ``metadata.continue_`` holds a token for the next page.
            continue_token: The ``metadata.continue_`` token from the previous page,
                to fetch the next one. Pass the same filters as for that page.
            version_match: How the API server should interpret ``resource_version``; sent
                as the Kubernetes ``resourceVersionMatch`` query parameter. See
                [Resource Version Semantics documentation](https://kubernetes.io/docs/reference/using-api/api-concepts/#semantics-for-get-and-list).
            resource_version: The resource version to list. If not provided,
                the current resource version will be listed. For details look at
                [Resource Version Semantics documentation](https://kubernetes.io/docs/reference/using-api/api-concepts/#semantics-for-get-and-list).
            request_timeout: HTTP-level timeout override for this call. A number is
                interpreted as the total timeout in seconds. Pass ``None`` to disable
                timeouts entirely for this call. Omit to use the client default.
            invalid: What to do with an object that does not fit the model.
                ``InvalidObjects.RAISE`` (the default) raises pydantic's
                ``ValidationError``. ``InvalidObjects.INCLUDE`` returns a
                ``ListWithInvalid`` that keeps such objects in ``invalid``, each an
                ``InvalidObject`` with its raw data, the error and its metadata.

        Returns:
            ListEntity[ResourceType]: the list of resources, with the list's
                ``metadata`` (``resource_version``, ``continue_``). A
                ``ListWithInvalid`` with ``invalid=InvalidObjects.INCLUDE``.

        Raises:
            ValueError: an argument is invalid, e.g. a namespace given for a
                cluster-scoped resource, or an unknown option value (e.g. for
                ``version_match``).
            ValidationError: an object does not fit the model (unless
                ``invalid=InvalidObjects.INCLUDE``), or the response is not a
                valid list; with ``INCLUDE``, also an object without a readable
                ``metadata.name``.
            KubexApiError: the API server rejected the request; the subclass
                matches the HTTP status (e.g. ``Forbidden``, ``UnprocessableEntity``).
            KubexConnectionError: the API server could not be reached.
            KubexTimeoutError: the request timed out on the client side.
            ConfigurationError: credentials could not be obtained, e.g. an exec
                plugin or OIDC token refresh failed.
        """
        invalid_objects = InvalidObjects(invalid)
        _namespace = ensure_optional_namespace(
            namespace, self._namespace, self._resource.__RESOURCE_CONFIG__.scope
        )
        options = ListOptions(
            label_selector=label_selector,
            field_selector=field_selector,
            timeout_seconds=timeout_seconds,
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
        if invalid_objects is InvalidObjects.INCLUDE:
            return _validate_list_with_invalid(
                self._resource, list_model, response.content
            )
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
            data: The resource instance to create.
            namespace: The namespace to create the resource in. If not provided,
                the namespace provided when creating the API will be used.
                The namespace is required for namespaced resources.
                If namespace is provided for cluster-scoped resources, an error will be raised.
            dry_run: Validate the request without persisting anything (``True``,
                ``"All"`` or ``DryRun.ALL``).
            field_manager: The field manager name recorded in ``managedFields`` as
                the owner of the fields this request sets.
            request_timeout: HTTP-level timeout override for this call. A number is
                interpreted as the total timeout in seconds. Pass ``None`` to disable
                timeouts entirely for this call. Omit to use the client default.

        Returns:
            ResourceType: the created resource instance, as stored by the API server.

        Raises:
            ValueError: an argument is invalid, e.g. a namespace that is missing for
                a namespace-scoped resource or given for a cluster-scoped one, or an
                unknown option value (e.g. for ``dry_run``).
            Conflict: a resource with this name already exists.
            KubexApiError: the API server rejected the request; the subclass
                matches the HTTP status (e.g. ``Forbidden``, ``UnprocessableEntity``).
            KubexConnectionError: the API server could not be reached.
            KubexTimeoutError: the request timed out on the client side.
            ConfigurationError: credentials could not be obtained, e.g. an exec
                plugin or OIDC token refresh failed.
        """
        _namespace = ensure_required_namespace(
            namespace, self._namespace, self._resource.__RESOURCE_CONFIG__.scope
        )
        options = PostOptions(dry_run=dry_run, field_manager=field_manager)
        request = self._request_builder.create(
            _namespace,
            options,
            data.model_dump_json(by_alias=True, exclude_none=True),
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
            dry_run: Validate the request without deleting anything (``True``,
                ``"All"`` or ``DryRun.ALL``).
            grace_period_seconds: The duration in seconds before the object should be
                deleted, overriding its default grace period. ``0`` deletes immediately.
            propagation_policy: Whether and how dependents are garbage collected:
                ``"Foreground"``, ``"Background"`` or ``"Orphan"`` (or the
                ``PropagationPolicy`` enum).
            preconditions: Conditions the object must meet to be deleted
                (``Precondition(uid=..., resource_version=...)``); the server returns
                ``409 Conflict`` if they don't hold.
            request_timeout: HTTP-level timeout override for this call. A number is
                interpreted as the total timeout in seconds. Pass ``None`` to disable
                timeouts entirely for this call. Omit to use the client default.

        Returns:
            Status: the resource has been fully deleted.
            ResourceType: deletion has started, but the resource still exists (e.g.
                it has finalizers or a termination grace period); the returned
                object has ``deletionTimestamp`` set. For details see
                [Resource deletion documentation](https://kubernetes.io/docs/reference/using-api/api-concepts/#resource-deletion).

        Raises:
            ValueError: an argument is invalid, e.g. an empty or malformed ``name``,
                a namespace that is missing for a namespace-scoped resource or given
                for a cluster-scoped one, or an unknown option value (e.g. for
                ``dry_run``).
            NotFound: the resource does not exist.
            Conflict: ``preconditions`` do not hold.
            KubexApiError: the API server rejected the request; the subclass
                matches the HTTP status (e.g. ``Forbidden``, ``UnprocessableEntity``).
            KubexConnectionError: the API server could not be reached.
            KubexTimeoutError: the request timed out on the client side.
            ConfigurationError: credentials could not be obtained, e.g. an exec
                plugin or OIDC token refresh failed.
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
        timeout_seconds: int | None = None,
        limit: int | None = None,
        continue_token: str | None = None,
        version_match: VersionMatchTypes = None,
        resource_version: ResourceVersionTypes = None,
        dry_run: DryRunTypes = None,
        grace_period_seconds: int | None = None,
        propagation_policy: PropagationPolicyTypes = None,
        preconditions: Precondition | None = None,
        request_timeout: ApiRequestTimeoutTypes = Ellipsis,
    ) -> Status | ListEntity[ResourceType]:
        """Delete collection of resources.

        Deletes every resource matching the filters in a single call. Without
        any selector, that is every resource of this type in the namespace (or,
        with ``namespace=None``, in all namespaces).

        Args:
            namespace: The namespace to delete resources in. If not provided,
                the namespace provided when creating the API will be used.
                Pass ``None`` to delete matching resources in all namespaces.
                If namespace is provided for cluster-scoped resources, an error will be raised.
            label_selector: Only delete resources whose labels match this selector.
                For details look at [Label Selectors documentation](https://kubernetes.io/docs/concepts/overview/working-with-objects/labels/#label-selectors).
            field_selector: Only delete resources whose fields match this selector.
                For details look at [Field Selectors documentation](https://kubernetes.io/docs/concepts/overview/working-with-objects/field-selectors/).
            timeout_seconds: Server-side timeout (in seconds) for the call;
                sent as the Kubernetes ``timeoutSeconds`` query parameter. For an
                HTTP client-side timeout, use ``request_timeout``.
            limit: Sent as the Kubernetes ``limit`` list option, as in ``list()``.
            continue_token: Sent as the Kubernetes ``continue`` list option, as in
                ``list()``.
            version_match: How the API server should interpret ``resource_version``; sent
                as the Kubernetes ``resourceVersionMatch`` query parameter.
            resource_version: The resource version at which to select the resources,
                as in ``list()``.
            dry_run: Validate the request without deleting anything (``True``,
                ``"All"`` or ``DryRun.ALL``).
            grace_period_seconds: The duration in seconds before each object should be
                deleted, overriding its default grace period. ``0`` deletes immediately.
            propagation_policy: Whether and how dependents are garbage collected:
                ``"Foreground"``, ``"Background"`` or ``"Orphan"`` (or the
                ``PropagationPolicy`` enum).
            preconditions: Conditions each object must meet to be deleted
                (``Precondition(uid=..., resource_version=...)``).
            request_timeout: HTTP-level timeout override for this call. A number is
                interpreted as the total timeout in seconds. Pass ``None`` to disable
                timeouts entirely for this call. Omit to use the client default.

        Returns:
            Status: the API server reported the result as a ``Status``.
            ListEntity[ResourceType]: the API server returned the list of deleted
                resources instead; which of the two you get depends on the
                Kubernetes version.

        Raises:
            ValueError: an argument is invalid, e.g. a namespace given for a
                cluster-scoped resource, or an unknown option value (e.g. for
                ``dry_run`` or ``version_match``).
            KubexApiError: the API server rejected the request; the subclass
                matches the HTTP status (e.g. ``Forbidden``, ``UnprocessableEntity``).
            KubexConnectionError: the API server could not be reached.
            KubexTimeoutError: the request timed out on the client side.
            ConfigurationError: credentials could not be obtained, e.g. an exec
                plugin or OIDC token refresh failed.
        """
        _namespace = ensure_optional_namespace(
            namespace, self._namespace, self._resource.__RESOURCE_CONFIG__.scope
        )
        list_options = ListOptions(
            label_selector=label_selector,
            field_selector=field_selector,
            timeout_seconds=timeout_seconds,
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
        field_validation: FieldValidationTypes = None,
        request_timeout: ApiRequestTimeoutTypes = Ellipsis,
    ) -> ResourceType:
        """Patch the specified resource.

        Args:
            name: The name of the resource to patch.
            patch: The patch to send: ``ApplyPatch`` (server-side apply),
                ``MergePatch``, ``StrategicMergePatch`` or ``JsonPatch``. Its type
                sets the request's ``Content-Type``.
            namespace: The namespace of the namespaced resource to patch. If not provided,
                the namespace provided when creating the API will be used.
                The namespace is required for namespaced resources.
                If namespace is provided for cluster-scoped resources, an error will be raised.
            dry_run: Validate the request without persisting anything (``True``,
                ``"All"`` or ``DryRun.ALL``).
            field_manager: The field manager name recorded in ``managedFields`` as
                the owner of the fields this patch sets. Required for ``ApplyPatch``.
            force: Take over fields currently owned by another field manager instead
                of failing with ``409 Conflict``. Only valid with ``ApplyPatch``.
            field_validation: How the API server handles unknown or duplicate fields in
                the patch: ``"Strict"`` (reject the request), ``"Warn"`` (accept it
                with a warning; the server default) or ``"Ignore"`` (drop them
                silently). Also accepts the ``FieldValidation`` enum.
            request_timeout: HTTP-level timeout override for this call. A number is
                interpreted as the total timeout in seconds. Pass ``None`` to disable
                timeouts entirely for this call. Omit to use the client default.

        Returns:
            ResourceType: the patched resource. An ``ApplyPatch`` for a resource
                that does not exist yet creates it and returns the new resource.

        Raises:
            ValueError: an argument is invalid, e.g. an empty or malformed ``name``,
                a namespace that is missing for a namespace-scoped resource or given
                for a cluster-scoped one, or an unknown option value (e.g. for
                ``dry_run`` or ``field_validation``).
            NotFound: the resource does not exist (an ``ApplyPatch`` creates it
                instead).
            Conflict: an ``ApplyPatch`` conflicts with fields owned by another
                field manager and ``force`` is not set.
            KubexApiError: the API server rejected the request; the subclass
                matches the HTTP status (e.g. ``Forbidden``, ``UnprocessableEntity``).
            KubexConnectionError: the API server could not be reached.
            KubexTimeoutError: the request timed out on the client side.
            ConfigurationError: credentials could not be obtained, e.g. an exec
                plugin or OIDC token refresh failed.
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
            name: The name of the resource to replace.
            data: The complete new state of the resource. If its
                ``metadata.resource_version`` is set (e.g. from a previous ``get()``),
                the request fails with ``409 Conflict`` when the resource has changed
                since that version.
            namespace: The namespace of the namespaced resource to replace. If not provided,
                the namespace provided when creating the API will be used.
                The namespace is required for namespaced resources.
                If namespace is provided for cluster-scoped resources, an error will be raised.
            dry_run: Validate the request without persisting anything (``True``,
                ``"All"`` or ``DryRun.ALL``).
            field_manager: The field manager name recorded in ``managedFields`` as
                the owner of the fields this request sets.
            request_timeout: HTTP-level timeout override for this call. A number is
                interpreted as the total timeout in seconds. Pass ``None`` to disable
                timeouts entirely for this call. Omit to use the client default.

        Returns:
            ResourceType: the replaced resource, as stored by the API server.

        Raises:
            ValueError: an argument is invalid, e.g. an empty or malformed ``name``,
                a namespace that is missing for a namespace-scoped resource or given
                for a cluster-scoped one, or an unknown option value (e.g. for
                ``dry_run``).
            NotFound: the resource does not exist.
            Conflict: the resource has changed since the
                ``metadata.resource_version`` that was sent.
            KubexApiError: the API server rejected the request; the subclass
                matches the HTTP status (e.g. ``Forbidden``, ``UnprocessableEntity``).
            KubexConnectionError: the API server could not be reached.
            KubexTimeoutError: the request timed out on the client side.
            ConfigurationError: credentials could not be obtained, e.g. an exec
                plugin or OIDC token refresh failed.
        """
        _namespace = ensure_required_namespace(
            namespace, self._namespace, self._resource.__RESOURCE_CONFIG__.scope
        )
        options = PostOptions(dry_run=dry_run, field_manager=field_manager)
        request = self._request_builder.replace(
            name,
            _namespace,
            options,
            data.model_dump_json(by_alias=True, exclude_none=True),
            request_timeout=request_timeout,
        )
        response = await self._client.request(request)
        return self._resource.model_validate_json(response.content)

    @overload
    def watch(
        self,
        *,
        namespace: ApiNamespaceTypes = Ellipsis,
        label_selector: str | None = None,
        field_selector: str | None = None,
        allow_bookmarks: bool | None = None,
        send_initial_events: bool | None = None,
        resource_version: ResourceVersionTypes = None,
        timeout_seconds: int | None = None,
        request_timeout: ApiRequestTimeoutTypes = Ellipsis,
        invalid: Literal[InvalidObjects.RAISE, "raise"] = InvalidObjects.RAISE,
    ) -> AsyncGenerator[WatchEvent[ResourceType], None]: ...

    @overload
    def watch(
        self,
        *,
        namespace: ApiNamespaceTypes = Ellipsis,
        label_selector: str | None = None,
        field_selector: str | None = None,
        allow_bookmarks: bool | None = None,
        send_initial_events: bool | None = None,
        resource_version: ResourceVersionTypes = None,
        timeout_seconds: int | None = None,
        request_timeout: ApiRequestTimeoutTypes = Ellipsis,
        invalid: Literal[InvalidObjects.INCLUDE, "include"],
    ) -> AsyncGenerator[WatchEvent[ResourceType] | InvalidWatchEvent, None]: ...

    @overload
    def watch(
        self,
        *,
        namespace: ApiNamespaceTypes = Ellipsis,
        label_selector: str | None = None,
        field_selector: str | None = None,
        allow_bookmarks: bool | None = None,
        send_initial_events: bool | None = None,
        resource_version: ResourceVersionTypes = None,
        timeout_seconds: int | None = None,
        request_timeout: ApiRequestTimeoutTypes = Ellipsis,
        invalid: InvalidObjectsTypes,
    ) -> AsyncGenerator[WatchEvent[ResourceType] | InvalidWatchEvent, None]: ...

    async def watch(
        self,
        *,
        namespace: ApiNamespaceTypes = Ellipsis,
        label_selector: str | None = None,
        field_selector: str | None = None,
        allow_bookmarks: bool | None = None,
        send_initial_events: bool | None = None,
        resource_version: ResourceVersionTypes = None,
        timeout_seconds: int | None = None,
        request_timeout: ApiRequestTimeoutTypes = Ellipsis,
        invalid: InvalidObjectsTypes = InvalidObjects.RAISE,
    ) -> AsyncGenerator[WatchEvent[ResourceType] | InvalidWatchEvent, None]:
        """Watch for changes to the specified resource.

        Args:
            namespace: The namespace to watch. If not provided,
                the namespace provided when creating the API will be used.
                Pass ``None`` to watch all namespaces.
                If namespace is provided for cluster-scoped resources, an error will be raised.
            label_selector: Only watch resources whose labels match this selector.
                For details look at [Label Selectors documentation](https://kubernetes.io/docs/concepts/overview/working-with-objects/labels/#label-selectors).
            field_selector: Only watch resources whose fields match this selector.
                For details look at [Field Selectors documentation](https://kubernetes.io/docs/concepts/overview/working-with-objects/field-selectors/).
            allow_bookmarks: Request periodic ``BOOKMARK`` events carrying a fresh
                ``resourceVersion``. Defaults to ``True`` when ``send_initial_events``
                is ``True`` (the server requires it); passing ``False`` together with
                ``send_initial_events=True`` raises ``ValueError``.
            send_initial_events: Start the stream with synthetic ``ADDED`` events for
                the current state, followed by a bookmark annotated with
                ``k8s.io/initial-events-end`` (see
                ``WatchEvent.is_initial_events_end``).
            resource_version: Only deliver changes made after this resource version,
                e.g. the list ``metadata.resource_version`` from a previous
                ``list()``. If not provided, the stream starts with synthetic
                ``ADDED`` events for every existing resource and then follows
                changes. For details look at
                [Resource Version Semantics documentation](https://kubernetes.io/docs/reference/using-api/api-concepts/#semantics-for-watch).
            timeout_seconds: Server-side timeout (in seconds); the server ends the
                stream cleanly after it.
            request_timeout: HTTP-level timeout override for this call. A number is
                interpreted as the total timeout in seconds. Pass ``None`` to disable
                timeouts entirely for this call. Omit to use the client's default
                for streams, which does not cut off an idle watch. An explicit
                short read/total timeout will terminate a quiet stream.
            invalid: What to do with an ``ADDED``, ``MODIFIED`` or ``DELETED``
                object that does not fit the model. ``InvalidObjects.RAISE`` (the
                default) raises pydantic's ``ValidationError``, which ends the
                stream. ``InvalidObjects.INCLUDE`` yields an ``InvalidWatchEvent``
                for it and the stream goes on.

        Yields:
            WatchEvent[ResourceType]: one event per change, with its ``type``
                (``ADDED``, ``MODIFIED``, ``DELETED`` or ``BOOKMARK``) and
                ``object`` (the resource, or a ``Bookmark`` for ``BOOKMARK``
                events). ``ERROR`` events are raised as exceptions instead. With
                ``invalid=InvalidObjects.INCLUDE``, an ``InvalidWatchEvent`` for
                each object that does not fit the model.

        Raises:
            ValueError: an argument is invalid, e.g. a namespace given for a
                cluster-scoped resource, or ``allow_bookmarks=False`` together with
                ``send_initial_events=True``.
            ValidationError: an object does not fit the model (unless
                ``invalid=InvalidObjects.INCLUDE``), or a bookmark does not parse;
                with ``INCLUDE``, also an object without a readable
                ``metadata.name``.
            Gone: the requested ``resource_version`` is too old (HTTP 410), either
                on connect or as an ``ERROR`` event mid-stream; re-list and watch
                again from the new ``resourceVersion``.
            KubexApiError: the API server rejected the request; the subclass
                matches the HTTP status (e.g. ``Forbidden``, ``UnprocessableEntity``).
            KubexConnectionError: the API server could not be reached, or the
                connection broke mid-stream.
            KubexTimeoutError: the request timed out on the client side, including
                mid-stream.
            ConfigurationError: credentials could not be obtained, e.g. an exec
                plugin or OIDC token refresh failed.
        """
        invalid_objects = InvalidObjects(invalid)
        _namespace = ensure_optional_namespace(
            namespace, self._namespace, self._resource.__RESOURCE_CONFIG__.scope
        )
        options = WatchOptions(
            label_selector=label_selector,
            field_selector=field_selector,
            allow_bookmarks=allow_bookmarks,
            send_initial_events=send_initial_events,
            resource_version=resource_version,
            timeout_seconds=timeout_seconds,
        )
        request = self._request_builder.watch(
            _namespace,
            options,
            request_timeout=request_timeout,
        )
        async for line in self._client.stream_lines(request):
            # Parse before yielding: the yield stays outside any ``except``, so an
            # exception thrown into the generator is never mistaken for ours.
            event = _parse_watch_event(
                self._resource, json.loads(line), invalid_objects
            )
            yield event


async def create_api(
    resource_type: Type[ResourceType],
    *,
    client: BaseClient | None = None,
    namespace: ApiNamespaceTypes = Ellipsis,
) -> Api[ResourceType]:
    """Create an API for the specified resource type.

    Args:
        resource_type: The resource type to create an API for.
        client: The client to use for the API. If not provided,
            a new client will be created.
        namespace: The namespace to use for the API. If set all
            operations will be performed in this namespace.
            The Api namespace can be overridden by passing a
            namespace to the individual methods. If omitted, a
            namespace-scoped resource falls back to the client's
            configured namespace (e.g. the in-cluster pod's own
            namespace); pass ``None`` explicitly for "all namespaces"
            instead. Cluster-scoped resources never receive a namespace.

    Returns:
        An Api instance for the specified resource type.

    Raises:
        ValueError: ``namespace`` is given for a cluster-scoped resource.
        ConfigurationError: no ``client`` was given and no configuration could be
            loaded (no usable kubeconfig, and not running inside a cluster).
        ImportError: no ``client`` was given and neither ``aiohttp`` nor ``httpx``
            is installed.
    """
    client = client or await create_client()
    return Api(resource_type, client=client, namespace=namespace)
