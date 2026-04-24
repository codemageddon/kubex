from enum import Enum

from kubex_core.models.interfaces import (
    Evictable,
    HasAttach,
    HasEphemeralContainers,
    HasExec,
    HasPortForward,
    HasResize,
    HasScaleSubresource,
    HasStatusSubresource,
)


class SubresourceConfiguration:
    def __init__(self, name: str, parent: type, url: str) -> None:
        self.name = name
        self.parent = parent
        self.url = url


class Subresource(Enum):
    STATUS = SubresourceConfiguration("status", HasStatusSubresource, "/status")
    SCALE = SubresourceConfiguration("scale", HasScaleSubresource, "/scale")
    EVICTION = SubresourceConfiguration("eviction", Evictable, "/eviction")
    EPHEMERAL_CONTAINERS = SubresourceConfiguration(
        "ephemeralcontainers", HasEphemeralContainers, "/ephemeralcontainers"
    )
    RESIZE = SubresourceConfiguration("resize", HasResize, "/resize")
    ATTACH = SubresourceConfiguration("attach", HasAttach, "/attach")
    EXEC = SubresourceConfiguration("exec", HasExec, "/exec")
    PORT_FORWARD = SubresourceConfiguration(
        "portforward", HasPortForward, "/portforward"
    )
