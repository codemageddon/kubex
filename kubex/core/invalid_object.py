"""Objects that do not fit their resource model.

``Api.list()`` and ``Api.watch()`` raise pydantic's ``ValidationError`` when an
object from the API server does not fit the model, for example a custom resource
stored before its CRD schema changed. With ``invalid=InvalidObjects.INCLUDE`` they
keep such an object as an ``InvalidObject`` instead, so one bad object neither
fails a whole list nor ends a watch.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Generic, Type, cast

from pydantic import Field, GetCoreSchemaHandler, ValidationError
from pydantic_core import core_schema

from kubex_core.models.list_entity import ListEntity
from kubex_core.models.metadata import ObjectMetadata
from kubex_core.models.typing import ResourceType


@dataclass(frozen=True, eq=False)
class InvalidObject:
    """An object from the API server that does not fit the resource model.

    Attributes:
        raw: The object as the server sent it.
        error: Why it does not fit the model.
        metadata: The object's metadata. It always parsed and always has a
            ``name``, so the object can still be identified, e.g. to drop it from
            a cache on a ``DELETED`` event.
    """

    raw: dict[str, Any]
    error: ValidationError
    metadata: ObjectMetadata

    def __repr__(self) -> str:
        return (
            f"InvalidObject(kind={self.raw.get('kind')!r}, "
            f"namespace={self.metadata.namespace!r}, name={self.metadata.name!r}, "
            f"errors={self.error.error_count()})"
        )

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source: Any, handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        # Lets ``ListWithInvalid`` hold these in a field; never parsed from JSON.
        return core_schema.is_instance_schema(cls)


class ListWithInvalid(ListEntity[ResourceType], Generic[ResourceType]):
    """A list whose objects that do not fit the model are kept apart.

    Returned by ``Api.list(invalid=InvalidObjects.INCLUDE)``. ``items`` holds the
    objects that fit the model, in server order; ``invalid`` holds the rest. The
    list's ``metadata`` (``resource_version``, ``continue_``) is the server's, so
    paging and watching from the list work as usual. ``invalid`` is not serialized.
    """

    invalid: list[InvalidObject] = Field(default_factory=list, exclude=True)


def _invalid_object_or_raise(raw: Any, error: ValidationError) -> InvalidObject:
    """Wrap ``raw``, which failed validation with ``error``, or re-raise ``error``.

    An object is only tolerated when its metadata parses and has a name: without
    one the caller cannot tell which object it is, which means the response
    itself is broken rather than one object in it.
    """
    if isinstance(raw, dict):
        try:
            metadata = ObjectMetadata.model_validate(raw.get("metadata"))
        except ValidationError:
            pass
        else:
            if metadata.name:
                return InvalidObject(raw=raw, error=error, metadata=metadata)
    raise error


def _validate_list_with_invalid(
    resource_type: Type[ResourceType],
    list_model: Type[ListEntity[ResourceType]],
    content: bytes,
) -> ListWithInvalid[ResourceType]:
    """Parse a list response, keeping items that do not fit ``resource_type`` apart.

    The list itself (``apiVersion``, ``kind``, ``metadata``) is validated as
    strictly as by ``list_model``; only its items are tolerated.
    """
    try:
        raw = json.loads(content)
    except ValueError:
        # Not JSON (or not UTF-8): raise the strict model's ``ValidationError``,
        # as without ``INCLUDE``. Should pydantic parse it after all, keep ours.
        list_model.model_validate_json(content)
        raise
    raw_items = raw.get("items") if isinstance(raw, dict) else None
    items: list[ResourceType] = []
    invalid: list[InvalidObject] = []
    if isinstance(raw_items, list):
        envelope = list_model.model_validate({**raw, "items": []})
        for raw_item in raw_items:
            try:
                items.append(resource_type.model_validate(raw_item))
            except ValidationError as error:
                invalid.append(_invalid_object_or_raise(raw_item, error))
    else:
        # No items (``null`` or missing), or not a list at all: nothing to
        # tolerate, so the strict model decides.
        envelope = list_model.model_validate(raw)
        items = list(envelope.items)
    model = cast(
        "Type[ListWithInvalid[ResourceType]]",
        cast(Any, ListWithInvalid)[resource_type],
    )
    return model.model_construct(
        envelope.model_fields_set,
        **(envelope.model_extra or {}),
        api_version=envelope.api_version,
        kind=envelope.kind,
        metadata=envelope.metadata,
        items=items,
        invalid=invalid,
    )
