from kubex.k8s.v1_37.admissionregistration.v1.apply_configuration import (
    ApplyConfiguration,
)
from kubex.k8s.v1_37.admissionregistration.v1.json_patch import JSONPatch
from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class Mutation(BaseK8sModel):
    """Mutation specifies the CEL expression which is used to apply the Mutation."""

    apply_configuration: ApplyConfiguration | None = Field(
        default=None,
        alias="applyConfiguration",
        description="applyConfiguration defines the desired configuration values of an object. The configuration is applied to the admission object using [structured merge diff](https://github.com/kubernetes-sigs/structured-merge-diff). A CEL expression is used to create apply configuration.",
    )
    json_patch: JSONPatch | None = Field(
        default=None,
        alias="jsonPatch",
        description="jsonPatch defines a [JSON patch](https://jsonpatch.com/) operation to perform a mutation to the object. A CEL expression is used to create the JSON patch.",
    )
    patch_type: str = Field(
        ...,
        alias="patchType",
        description='patchType indicates the patch strategy used. Allowed values are "ApplyConfiguration" and "JSONPatch". Required.',
    )
