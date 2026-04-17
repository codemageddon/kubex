from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class SeccompProfile(BaseK8sModel):
    """SeccompProfile defines a pod/container's seccomp profile settings. Only one profile source may be set."""

    localhost_profile: str | None = Field(
        default=None,
        alias="localhostProfile",
        description='localhostProfile indicates a profile defined in a file on the node should be used. The profile must be preconfigured on the node to work. Must be a descending path, relative to the kubelet\'s configured seccomp profile location. Must be set if type is "Localhost". Must NOT be set for any other type.',
    )
    type_: str = Field(
        ...,
        alias="type",
        description="type indicates which kind of seccomp profile will be applied. Valid options are: Localhost - a profile defined in a file on the node should be used. RuntimeDefault - the container runtime default profile should be used. Unconfined - no profile should be applied.",
    )
