from kubex.k8s.v1_35.core.v1.pod_dns_config_option import PodDNSConfigOption
from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class PodDNSConfig(BaseK8sModel):
    """PodDNSConfig defines the DNS parameters of a pod in addition to those generated from DNSPolicy."""

    nameservers: list[str] | None = Field(
        default=None,
        alias="nameservers",
        description="A list of DNS name server IP addresses. This will be appended to the base nameservers generated from DNSPolicy. Duplicated nameservers will be removed.",
    )
    options: list[PodDNSConfigOption] | None = Field(
        default=None,
        alias="options",
        description="A list of DNS resolver options. This will be merged with the base options generated from DNSPolicy. Duplicated entries will be removed. Resolution options given in Options will override those that appear in the base DNSPolicy.",
    )
    searches: list[str] | None = Field(
        default=None,
        alias="searches",
        description="A list of DNS search domains for host-name lookup. This will be appended to the base search paths generated from DNSPolicy. Duplicated search paths will be removed.",
    )
