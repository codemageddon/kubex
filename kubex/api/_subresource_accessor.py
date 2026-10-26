from __future__ import annotations

from typing import ClassVar, Generic, Type

from kubex.client.client import BaseClient
from kubex.core.params import (
    DryRunTypes,
    FieldValidationTypes,
    NamespaceTypes,
    PatchOptions,
    PostOptions,
)
from kubex.core.patch import Patch
from kubex.core.request_builder.builder import RequestBuilder
from kubex_core.models.resource_config import Scope
from kubex_core.models.typing import ResourceType

from ._protocol import (
    ApiNamespaceTypes,
    ApiRequestTimeoutTypes,
    ensure_required_namespace,
)


class ResourceSubresourceAccessor(Generic[ResourceType]):
    """Shared get/replace/patch implementation for a subresource whose body is a full
    `ResourceType` (status, resize, ephemeral containers) rather than a distinct shape
    of its own (unlike scale/eviction). Subclasses set `_subresource`.
    """

    _subresource: ClassVar[str]

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
        request_timeout: ApiRequestTimeoutTypes = Ellipsis,
    ) -> ResourceType:
        """Read this subresource of the specified resource.

        Args:
            name: The name of the resource to read.
            namespace: The namespace of the namespaced resource to read. If not provided,
                the namespace provided when creating the API will be used.
                The namespace is required for namespaced resources.
                If namespace is provided for cluster-scoped resources, an error will be raised.
            request_timeout: HTTP-level timeout override for this call. A number is
                interpreted as the total timeout in seconds. Pass ``None`` to disable
                timeouts entirely for this call. Omit to use the client default.

        Returns:
            ResourceType: the full resource, as returned by the subresource endpoint.

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
        request = self._request_builder.get_subresource(
            self._subresource, name, _namespace, request_timeout=request_timeout
        )
        response = await self._client.request(request)
        return self._resource_type.model_validate_json(response.content)

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
        """Replace this subresource of the specified resource.

        Args:
            name: The name of the resource whose subresource to replace.
            data: The resource carrying the new subresource content. The API server
                only persists the part this subresource covers (e.g. ``.status`` for
                the status subresource). If its ``metadata.resource_version`` is set
                (e.g. from a previous ``get()``), the request fails with
                ``409 Conflict`` when the resource has changed since that version.
            namespace: The namespace of the namespaced resource. If not provided,
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
            ResourceType: the full resource after the update, as stored by the API
                server.

        Raises:
            ValueError: an argument is invalid, e.g. an empty or malformed ``name``,
                a namespace that is missing for a namespace-scoped resource or given
                for a cluster-scoped one, or an unknown option value (e.g. for
                ``dry_run``).
            NotFound: the resource does not exist.
            Conflict: the resource has changed since the ``metadata.resource_version``
                that was sent.
            KubexApiError: the API server rejected the request; the subclass
                matches the HTTP status (e.g. ``Forbidden``, ``UnprocessableEntity``).
            KubexConnectionError: the API server could not be reached.
            KubexTimeoutError: the request timed out on the client side.
            ConfigurationError: credentials could not be obtained, e.g. an exec
                plugin or OIDC token refresh failed.
        """
        _namespace = ensure_required_namespace(namespace, self._namespace, self._scope)
        options = PostOptions(dry_run=dry_run, field_manager=field_manager)
        request = self._request_builder.replace_subresource(
            self._subresource,
            name,
            _namespace,
            data=data.model_dump_json(by_alias=True, exclude_none=True),
            options=options,
            request_timeout=request_timeout,
        )
        response = await self._client.request(request)
        return self._resource_type.model_validate_json(response.content)

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
        """Patch this subresource of the specified resource.

        Args:
            name: The name of the resource whose subresource to patch.
            patch: The patch to send: ``ApplyPatch`` (server-side apply),
                ``MergePatch``, ``StrategicMergePatch`` or ``JsonPatch``. Its type
                sets the request's ``Content-Type``. The API server only persists
                the part this subresource covers.
            namespace: The namespace of the namespaced resource. If not provided,
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
            ResourceType: the full resource after the patch, as stored by the API
                server.

        Raises:
            ValueError: an argument is invalid, e.g. an empty or malformed ``name``,
                a namespace that is missing for a namespace-scoped resource or given
                for a cluster-scoped one, or an unknown option value (e.g. for
                ``dry_run``).
            NotFound: the resource does not exist.
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
        request = self._request_builder.patch_subresource(
            self._subresource,
            name,
            _namespace,
            options=options,
            patch=patch,
            request_timeout=request_timeout,
        )
        response = await self._client.request(request)
        return self._resource_type.model_validate_json(response.content)
