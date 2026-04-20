from pydantic import Field

from kubex.k8s.v1_33.apiextensions_k8s_io.v1.webhook_client_config import (
    WebhookClientConfig,
)
from kubex_core.models.base import BaseK8sModel


class WebhookConversion(BaseK8sModel):
    """WebhookConversion describes how to call a conversion webhook"""

    client_config: WebhookClientConfig | None = Field(
        default=None,
        alias="clientConfig",
        description="clientConfig is the instructions for how to call the webhook if strategy is `Webhook`.",
    )
    conversion_review_versions: list[str] = Field(
        ...,
        alias="conversionReviewVersions",
        description="conversionReviewVersions is an ordered list of preferred `ConversionReview` versions the Webhook expects. The API server will use the first version in the list which it supports. If none of the versions specified in this list are supported by API server, conversion will fail for the custom resource. If a persisted Webhook configuration specifies allowed versions and does not include any versions known to the API Server, calls to the webhook will fail.",
    )
