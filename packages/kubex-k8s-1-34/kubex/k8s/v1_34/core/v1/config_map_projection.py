from kubex.k8s.v1_34.core.v1.key_to_path import KeyToPath
from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class ConfigMapProjection(BaseK8sModel):
    """Adapts a ConfigMap into a projected volume. The contents of the target ConfigMap's Data field will be presented in a projected volume as files using the keys in the Data field as the file names, unless the items element is populated with specific mappings of keys to paths. Note that this is identical to a configmap volume source without the default mode."""

    items: list[KeyToPath] | None = Field(
        default=None,
        alias="items",
        description="items if unspecified, each key-value pair in the Data field of the referenced ConfigMap will be projected into the volume as a file whose name is the key and content is the value. If specified, the listed keys will be projected into the specified paths, and unlisted keys will not be present. If a key is specified which is not present in the ConfigMap, the volume setup will error unless it is marked optional. Paths must be relative and may not contain the '..' path or start with '..'.",
    )
    name: str | None = Field(
        default=None,
        alias="name",
        description="Name of the referent. This field is effectively required, but due to backwards compatibility is allowed to be empty. Instances of this type with an empty value here are almost certainly wrong. More info: https://kubernetes.io/docs/concepts/overview/working-with-objects/names/#names",
    )
    optional: bool | None = Field(
        default=None,
        alias="optional",
        description="optional specify whether the ConfigMap or its keys must be defined",
    )
