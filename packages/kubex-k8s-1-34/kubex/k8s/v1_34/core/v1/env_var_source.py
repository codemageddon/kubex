from kubex.k8s.v1_34.core.v1.config_map_key_selector import ConfigMapKeySelector
from kubex.k8s.v1_34.core.v1.file_key_selector import FileKeySelector
from kubex.k8s.v1_34.core.v1.object_field_selector import ObjectFieldSelector
from kubex.k8s.v1_34.core.v1.resource_field_selector import ResourceFieldSelector
from kubex.k8s.v1_34.core.v1.secret_key_selector import SecretKeySelector
from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class EnvVarSource(BaseK8sModel):
    """EnvVarSource represents a source for the value of an EnvVar."""

    config_map_key_ref: ConfigMapKeySelector | None = Field(
        default=None,
        alias="configMapKeyRef",
        description="Selects a key of a ConfigMap.",
    )
    field_ref: ObjectFieldSelector | None = Field(
        default=None,
        alias="fieldRef",
        description="Selects a field of the pod: supports metadata.name, metadata.namespace, `metadata.labels['<KEY>']`, `metadata.annotations['<KEY>']`, spec.nodeName, spec.serviceAccountName, status.hostIP, status.podIP, status.podIPs.",
    )
    file_key_ref: FileKeySelector | None = Field(
        default=None,
        alias="fileKeyRef",
        description="FileKeyRef selects a key of the env file. Requires the EnvFiles feature gate to be enabled.",
    )
    resource_field_ref: ResourceFieldSelector | None = Field(
        default=None,
        alias="resourceFieldRef",
        description="Selects a resource of the container: only resources limits and requests (limits.cpu, limits.memory, limits.ephemeral-storage, requests.cpu, requests.memory and requests.ephemeral-storage) are currently supported.",
    )
    secret_key_ref: SecretKeySelector | None = Field(
        default=None,
        alias="secretKeyRef",
        description="Selects a key of a secret in the pod's namespace",
    )
