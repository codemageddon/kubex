from kubex.k8s.v1_35.networking.v1.http_ingress_path import HTTPIngressPath
from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class HTTPIngressRuleValue(BaseK8sModel):
    """HTTPIngressRuleValue is a list of http selectors pointing to backends. In the example: http://<host>/<path>?<searchpart> -> backend where where parts of the url correspond to RFC 3986, this resource will be used to match against everything after the last '/' and before the first '?' or '#'."""

    paths: list[HTTPIngressPath] = Field(
        ...,
        alias="paths",
        description="paths is a collection of paths that map requests to backends.",
    )
