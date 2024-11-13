from __future__ import annotations

from typing import TYPE_CHECKING, TypeVar

if TYPE_CHECKING:
    from kubex.models.base_entity import BaseEntity  # noqa: F401


ResourceType = TypeVar("ResourceType", bound="BaseEntity")
