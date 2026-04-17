from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class AppArmorProfile(BaseK8sModel):
    """AppArmorProfile defines a pod or container's AppArmor settings."""

    localhost_profile: str | None = Field(
        default=None,
        alias="localhostProfile",
        description='localhostProfile indicates a profile loaded on the node that should be used. The profile must be preconfigured on the node to work. Must match the loaded name of the profile. Must be set if and only if type is "Localhost".',
    )
    type_: str = Field(
        ...,
        alias="type",
        description="type indicates which kind of AppArmor profile will be applied. Valid options are: Localhost - a profile pre-loaded on the node. RuntimeDefault - the container runtime's default profile. Unconfined - no AppArmor enforcement.",
    )
