from kubex.core.params import PatchOptions, PostOptions
from kubex.core.patch import (
    Patch,
)
from kubex.models.interfaces import HasScaleSubresource
from kubex.models.scale import Scale
from kubex.models.typing import ResourceType

from ._protocol import ApiProtocol


class ScaleMixin(ApiProtocol[ResourceType]):
    def _check_implemented(self) -> None:
        if not issubclass(self._resource, HasScaleSubresource):
            raise NotImplementedError(
                "Scale is only supported for resources with replicas"
            )

    async def get_scale(self, name: str) -> Scale:
        self._check_implemented()
        self._check_namespace()
        request = self._request_builder.get_subresource("scale", name)
        response = await self._client.request(request)
        return Scale.model_validate_json(response.content)

    async def replace_scale(
        self, name: str, scale: Scale, options: PostOptions | None = None
    ) -> Scale:
        self._check_implemented()
        self._check_namespace()
        request = self._request_builder.replace_subresource(
            "scale",
            name,
            data=scale.model_dump_json(
                by_alias=True, exclude_unset=True, exclude_none=True
            ),
            options=options or PostOptions.default(),
        )
        response = await self._client.request(request)
        return Scale.model_validate_json(response.content)

    async def patch_scale(
        self,
        name: str,
        patch: Patch,
        options: PatchOptions | None = None,
    ) -> Scale:
        self._check_implemented()
        self._check_namespace()
        request = self._request_builder.patch_subresource(
            "scale",
            name,
            options=options or PatchOptions.default(),
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
