from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class NodeRuntimeHandlerFeatures(BaseK8sModel):
    """NodeRuntimeHandlerFeatures is a set of features implemented by the runtime handler."""

    recursive_read_only_mounts: bool | None = Field(
        default=None,
        alias="recursiveReadOnlyMounts",
        description="RecursiveReadOnlyMounts is set to true if the runtime handler supports RecursiveReadOnlyMounts.",
    )
    user_namespaces: bool | None = Field(
        default=None,
        alias="userNamespaces",
        description="UserNamespaces is set to true if the runtime handler supports UserNamespaces, including for volumes.",
    )
