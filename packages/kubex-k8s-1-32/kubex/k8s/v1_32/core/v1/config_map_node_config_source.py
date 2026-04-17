from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class ConfigMapNodeConfigSource(BaseK8sModel):
    """ConfigMapNodeConfigSource contains the information to reference a ConfigMap as a config source for the Node. This API is deprecated since 1.22: https://git.k8s.io/enhancements/keps/sig-node/281-dynamic-kubelet-configuration"""

    kubelet_config_key: str = Field(
        ...,
        alias="kubeletConfigKey",
        description="KubeletConfigKey declares which key of the referenced ConfigMap corresponds to the KubeletConfiguration structure This field is required in all cases.",
    )
    name: str = Field(
        ...,
        alias="name",
        description="Name is the metadata.name of the referenced ConfigMap. This field is required in all cases.",
    )
    namespace: str = Field(
        ...,
        alias="namespace",
        description="Namespace is the metadata.namespace of the referenced ConfigMap. This field is required in all cases.",
    )
    resource_version: str | None = Field(
        default=None,
        alias="resourceVersion",
        description="ResourceVersion is the metadata.ResourceVersion of the referenced ConfigMap. This field is forbidden in Node.Spec, and required in Node.Status.",
    )
    uid: str | None = Field(
        default=None,
        alias="uid",
        description="UID is the metadata.UID of the referenced ConfigMap. This field is forbidden in Node.Spec, and required in Node.Status.",
    )
