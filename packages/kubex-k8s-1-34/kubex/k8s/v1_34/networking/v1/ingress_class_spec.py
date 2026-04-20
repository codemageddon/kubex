from pydantic import Field

from kubex.k8s.v1_34.networking.v1.ingress_class_parameters_reference import (
    IngressClassParametersReference,
)
from kubex_core.models.base import BaseK8sModel


class IngressClassSpec(BaseK8sModel):
    """IngressClassSpec provides information about the class of an Ingress."""

    controller: str | None = Field(
        default=None,
        alias="controller",
        description='controller refers to the name of the controller that should handle this class. This allows for different "flavors" that are controlled by the same controller. For example, you may have different parameters for the same implementing controller. This should be specified as a domain-prefixed path no more than 250 characters in length, e.g. "acme.io/ingress-controller". This field is immutable.',
    )
    parameters: IngressClassParametersReference | None = Field(
        default=None,
        alias="parameters",
        description="parameters is a link to a custom resource containing additional configuration for the controller. This is optional if the controller does not require extra parameters.",
    )
