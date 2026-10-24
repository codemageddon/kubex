from __future__ import annotations

import json
from typing import AsyncGenerator, Generic, Type

from kubex.client.client import BaseClient
from kubex.core.params import (
    DryRunTypes,
    FieldValidationTypes,
    GetOptions,
    ListOptions,
    NamespaceTypes,
    PatchOptions,
    ResourceVersionTypes,
    VersionMatchTypes,
    WatchOptions,
)
from kubex.core.patch import Patch
from kubex.core.request_builder.builder import RequestBuilder
from kubex.core.watch_event import WatchEvent
from kubex_core.models.list_entity import ListEntity
from kubex_core.models.partial_object_meta import PartialObjectMetadata
from kubex_core.models.resource_config import Scope
from kubex_core.models.typing import ResourceType

from ._protocol import (
    ApiNamespaceTypes,
    ApiRequestTimeoutTypes,
    ensure_optional_namespace,
    ensure_required_namespace,
)


class MetadataAccessor(Generic[ResourceType]):
    """Accessor for metadata subresource operations."""

    def __init__(
        self,
        client: BaseClient,
        request_builder: RequestBuilder,
        namespace: NamespaceTypes,
        scope: Scope,
        resource_type: Type[ResourceType],
    ) -> None:
        self._client = client
        self._request_builder = request_builder
        self._namespace = namespace
        self._scope = scope
        self._resource_type = resource_type

    async def get(
        self,
        name: str,
        *,
        namespace: ApiNamespaceTypes = Ellipsis,
        resource_version: ResourceVersionTypes = None,
        request_timeout: ApiRequestTimeoutTypes = Ellipsis,
    ) -> PartialObjectMetadata:
        """Read metadata of the specified resource.

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
            PartialObjectMetadata: the resource's ``api_version``, ``kind`` and
                ``metadata``, without its spec or status.

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
        _namespace = ensure_required_namespace(namespace, self._namespace, self._scope)
        options = GetOptions(resource_version=resource_version)
        request = self._request_builder.get_metadata(
            name, _namespace, options=options, request_timeout=request_timeout
        )
        response = await self._client.request(request)
        return PartialObjectMetadata.model_validate_json(response.content)

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
    ) -> ListEntity[PartialObjectMetadata]:
        """List metadata of resources.

        Args:
            namespace: The namespace of the namespaced resources to list. If not provided,
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

        Returns:
            ListEntity[PartialObjectMetadata]: the metadata of the matching resources,
                with the list's ``metadata`` (``resource_version``, ``continue_``).

        Raises:
            ValueError: an argument is invalid, e.g. a namespace given for a
                cluster-scoped resource, or an unknown option value (e.g. for
                ``version_match``).
            KubexApiError: the API server rejected the request; the subclass
                matches the HTTP status (e.g. ``Forbidden``, ``UnprocessableEntity``).
            KubexConnectionError: the API server could not be reached.
            KubexTimeoutError: the request timed out on the client side.
            ConfigurationError: credentials could not be obtained, e.g. an exec
                plugin or OIDC token refresh failed.
        """
        _namespace = ensure_optional_namespace(namespace, self._namespace, self._scope)
        options = ListOptions(
            label_selector=label_selector,
            field_selector=field_selector,
            timeout_seconds=timeout_seconds,
            limit=limit,
            continue_token=continue_token,
            version_match=version_match,
            resource_version=resource_version,
        )
        request = self._request_builder.list_metadata(
            _namespace, options, request_timeout=request_timeout
        )
        response = await self._client.request(request)
        model = PartialObjectMetadata.__RESOURCE_CONFIG__.list_model
        return model.model_validate_json(response.content)

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
    ) -> PartialObjectMetadata:
        """Patch metadata of the specified resource.

        The patch is applied to the resource itself; only the response is reduced
        to its metadata.

        Args:
            name: The name of the resource to patch.
            patch: The patch to send, typically changing labels or annotations:
                ``ApplyPatch`` (server-side apply), ``MergePatch``,
                ``StrategicMergePatch`` or ``JsonPatch``. Its type sets the request's
                ``Content-Type``. An ``ApplyPatch`` body is sent with the target
                resource's ``apiVersion`` and ``kind``.
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
            PartialObjectMetadata: the patched resource's ``api_version``, ``kind``
                and ``metadata``.

        Raises:
            ValueError: an argument is invalid, e.g. an empty or malformed ``name``,
                a namespace that is missing for a namespace-scoped resource or given
                for a cluster-scoped one, or an unknown option value (e.g. for
                ``dry_run``).
            NotFound: the resource does not exist (an ``ApplyPatch`` creates it
                instead).
            Conflict: an ``ApplyPatch`` conflicts with fields owned by another field
                manager and ``force`` is not set.
            KubexApiError: the API server rejected the request; the subclass
                matches the HTTP status (e.g. ``Forbidden``, ``UnprocessableEntity``).
            KubexConnectionError: the API server could not be reached.
            KubexTimeoutError: the request timed out on the client side.
            ConfigurationError: credentials could not be obtained, e.g. an exec
                plugin or OIDC token refresh failed.
        """
        _namespace = ensure_required_namespace(namespace, self._namespace, self._scope)
        options = PatchOptions(
            dry_run=dry_run,
            field_manager=field_manager,
            force=force,
            field_validation=field_validation,
        )
        request = self._request_builder.patch_metadata(
            name, _namespace, options, patch, request_timeout=request_timeout
        )
        response = await self._client.request(request)
        return PartialObjectMetadata.model_validate_json(response.content)

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
    ) -> AsyncGenerator[
        WatchEvent[PartialObjectMetadata],
        None,
    ]:
        """Watch for metadata changes of resources.

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
                ``k8s.io/initial-events-end``.
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

        Yields:
            WatchEvent[PartialObjectMetadata]: one event per change, with its ``type``
                (``ADDED``, ``MODIFIED``, ``DELETED`` or ``BOOKMARK``) and ``object``
                (the resource's metadata, or a ``Bookmark`` for ``BOOKMARK`` events).
                ``ERROR`` events are raised as exceptions instead.

        Raises:
            ValueError: an argument is invalid, e.g. a namespace given for a
                cluster-scoped resource, an unknown option value (e.g. for
                ``version_match``), or ``allow_bookmarks=False`` together with
                ``send_initial_events=True``.
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
        _namespace = ensure_optional_namespace(namespace, self._namespace, self._scope)
        options = WatchOptions(
            label_selector=label_selector,
            field_selector=field_selector,
            allow_bookmarks=allow_bookmarks,
            send_initial_events=send_initial_events,
            timeout_seconds=timeout_seconds,
            resource_version=resource_version,
        )
        request = self._request_builder.watch_metadata(
            _namespace,
            options,
            request_timeout=request_timeout,
        )
        async for line in self._client.stream_lines(request):
            yield WatchEvent(PartialObjectMetadata, json.loads(line))
