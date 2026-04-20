from pydantic import Field

from kubex.k8s.v1_37.apiextensions_k8s_io.v1.webhook_conversion import WebhookConversion
from kubex_core.models.base import BaseK8sModel


class CustomResourceConversion(BaseK8sModel):
    """CustomResourceConversion describes how to convert different versions of a CR."""

    strategy: str = Field(
        ...,
        alias="strategy",
        description='strategy specifies how custom resources are converted between versions. Allowed values are: - `"None"`: The converter only change the apiVersion and would not touch any other field in the custom resource. - `"Webhook"`: API Server will call to an external webhook to do the conversion. Additional information is needed for this option. This requires spec.preserveUnknownFields to be false, and spec.conversion.webhook to be set.',
    )
    webhook: WebhookConversion | None = Field(
        default=None,
        alias="webhook",
        description='webhook describes how to call the conversion webhook. Required when `strategy` is set to `"Webhook"`.',
    )
