from __future__ import annotations

from kubex.core.params import (
    DryRunTypes,
    FieldValidation,
    PatchOptions,
    PostOptions,
)
from kubex.core.patch import Patch
from kubex.models.interfaces import HasScaleSubresource
from kubex.models.scale import Scale
from kubex.models.typing import ResourceType

from ._protocol import ApiNamespaceTypes, ApiProtocol

SCALE_SUBRESOURCE = "scale"


class ScaleMixin(ApiProtocol[ResourceType]):
    def _check_implemented(self) -> None:
        if not issubclass(self._resource, HasScaleSubresource):
            raise NotImplementedError(
                "Scale is only supported for resources with replicas"
            )

    async def get_scale(
        self, name: str, *, namespace: ApiNamespaceTypes = Ellipsis
    ) -> Scale:
        self._check_implemented()
        _namespace = self._ensure_required_namespace(namespace)
        request = self._request_builder.get_subresource(
            SCALE_SUBRESOURCE, name, _namespace
        )
        response = await self._client.request(request)
        return Scale.model_validate_json(response.content)

    async def replace_scale(
        self,
        name: str,
        scale: Scale,
        *,
        namespace: ApiNamespaceTypes = Ellipsis,
        dry_run: DryRunTypes = None,
        field_manager: str | None = None,
    ) -> Scale:
        self._check_implemented()
        _namespace = self._ensure_required_namespace(namespace)
        options = PostOptions(dry_run=dry_run, field_manager=field_manager)
        request = self._request_builder.replace_subresource(
            SCALE_SUBRESOURCE,
            name,
            _namespace,
            data=scale.model_dump_json(
                by_alias=True, exclude_unset=True, exclude_none=True
            ),
            options=options,
        )
        response = await self._client.request(request)
        return Scale.model_validate_json(response.content)

    async def patch_scale(
        self,
        name: str,
        patch: Patch,
        *,
        namespace: ApiNamespaceTypes = Ellipsis,
        options: PatchOptions | None = None,
        dry_run: DryRunTypes = None,
        field_manager: str | None = None,
        force: bool | None = None,
        field_validation: FieldValidation | None = None,
    ) -> Scale:
        self._check_implemented()
        _namespace = self._ensure_required_namespace(namespace)
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
        )
        response = await self._client.request(request)
        return Scale.model_validate_json(response.content)


# class _SubresourceMixin(ApiProtocol[ResourceType]):
#     def _check_subresource(self, surecesource: Subresource) -> None:
#         parent_required = surecesource.value
#         if not issubclass(self._resource, parent_required):
#             raise NotImplementedError(
#                 f"{self._resource.__RESOURCE_CONFIG__.kind} from {self._resource.__RESOURCE_CONFIG__.api_version} has no {surecesource.name.lower()} subresource"
#             )

#     async def get_subresource(
#         self, name: str, subresource: Subresource
#     ) -> ResourceType:
#         self._check_subresource(subresource)
#         self._check_namespace()
#         request = self._request_builder.get_subresource(name, subresource)
#         async with self._client.get_client() as client:
#             response = await client.get(request.url, params=request.query_params)
#             response.raise_for_status()
#             return self._resource.model_validate_json(response.content)

#     async def patch_subresource(
#         self, name: str, subresource: str, patch: dict[str, str]
#     ) -> ResourceType:
#         self._check_namespace()
#         request = self._request_builder.patch_subresource(name, subresource, patch)
#         async with self._client.get_client() as client:
#             response = await client.patch(
#                 request.url,
#                 data=patch,
#                 headers={"Content-Type": "application/merge-patch+json"},
#             )
#             response.raise_for_status()
#             return self._resource.model_validate_json(response.content)

#     async def replace_subresource(
#         self, name: str, subresource: str, body: ResourceType
#     ) -> ResourceType:
#         self._check_namespace()
#         request = self._request_builder.replace_subresource(name, subresource, body)
#         async with self._client.get_client() as client:
#             response = await client.put(
#                 request.url,
#                 data=body.json(),
#                 headers={"Content-Type": "application/json"},
#             )
#             response.raise_for_status()
#             return self._resource.model_validate_json(response.content)
