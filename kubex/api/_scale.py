from __future__ import annotations

from typing import Any, Generic, Type, TypeVar, overload

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
from kubex_core.models.interfaces import HasScaleSubresource
from kubex_core.models.resource_config import Scope
from kubex_core.models.scale import Scale
from kubex_core.models.typing import ResourceType

from ._protocol import (
    ApiNamespaceTypes,
    ApiProtocol,
    ApiRequestTimeoutTypes,
    CachedSubresourceDescriptor,
    SubresourceNotAvailable,
    ensure_required_namespace,
)

_S = TypeVar("_S", bound=HasScaleSubresource)

SCALE_SUBRESOURCE = "scale"


class ScaleAccessor(Generic[ResourceType]):
    """Accessor for scale subresource operations."""

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
    ) -> Scale:
        """Read the scale of the specified resource.

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
            Scale: the resource's scale: ``spec.replicas`` is the desired replica
                count and ``status.replicas`` the observed one.

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
            SCALE_SUBRESOURCE, name, _namespace, request_timeout=request_timeout
        )
        response = await self._client.request(request)
        return Scale.model_validate_json(response.content)

    async def replace(
        self,
        name: str,
        scale: Scale,
        *,
        namespace: ApiNamespaceTypes = Ellipsis,
        dry_run: DryRunTypes = None,
        field_manager: str | None = None,
        request_timeout: ApiRequestTimeoutTypes = Ellipsis,
    ) -> Scale:
        """Replace the scale of the specified resource.

        Args:
            name: The name of the resource whose scale to replace.
            scale: The new scale, usually the ``Scale`` from ``get()`` with
                ``spec.replicas`` changed. If its ``metadata.resource_version`` is set,
                the request fails with ``409 Conflict`` when the resource has changed
                since that version.
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
            Scale: the updated scale.

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
            SCALE_SUBRESOURCE,
            name,
            _namespace,
            data=scale.model_dump_json(by_alias=True, exclude_none=True),
            options=options,
            request_timeout=request_timeout,
        )
        response = await self._client.request(request)
        return Scale.model_validate_json(response.content)

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
    ) -> Scale:
        """Patch the scale of the specified resource.

        Args:
            name: The name of the resource whose scale to patch.
            patch: The patch to send: ``ApplyPatch`` (server-side apply),
                ``MergePatch``, ``StrategicMergePatch`` or ``JsonPatch``, e.g. a
                ``MergePatch`` setting ``spec.replicas``. Its type sets the
                request's ``Content-Type``.
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
            Scale: the scale after the patch.

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
            SCALE_SUBRESOURCE,
            name,
            _namespace,
            options=options,
            patch=patch,
            request_timeout=request_timeout,
        )
        response = await self._client.request(request)
        return Scale.model_validate_json(response.content)


class _ScaleDescriptor(CachedSubresourceDescriptor):
    _marker = HasScaleSubresource
    _accessor_cls = ScaleAccessor
    _error_message = (
        "Scale is only supported for resources with HasScaleSubresource marker"
    )

    @overload
    def __get__(self, instance: None, owner: type) -> _ScaleDescriptor: ...

    @overload
    def __get__(self, instance: ApiProtocol[_S], owner: type) -> ScaleAccessor[_S]: ...

    @overload
    def __get__(
        self, instance: ApiProtocol[Any], owner: type
    ) -> SubresourceNotAvailable: ...

    def __get__(self, instance: Any, owner: type | None = None) -> Any:
        return self._resolve(instance)
