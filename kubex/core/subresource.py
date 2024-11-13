from enum import Enum

from kubex.models.interfaces import HasScaleSubresource, HasStatusSubresource


class SubresourceConfiguration:
    def __init__(self, name: str, parent: type, url: str) -> None:
        self.name = name
        self.parent = parent
        self.url = url


class Subresource(Enum):
    STATUS = SubresourceConfiguration("status", HasStatusSubresource, "/status")
    SCALE = SubresourceConfiguration("scale", HasScaleSubresource, "/scale")
