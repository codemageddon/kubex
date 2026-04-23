from __future__ import annotations

from typing import Literal

from .base import BaseK8sModel
from .metadata import ObjectMetadata


class DeleteOptions(BaseK8sModel):
    """Minimal representation of meta/v1 DeleteOptions for use in Eviction."""

    dry_run: list[str] | None = None
    grace_period_seconds: int | None = None
    propagation_policy: str | None = None


class Eviction(BaseK8sModel):
    """Eviction evicts a pod from its node subject to certain policies and safety constraints.

    This is a minimal model for the policy/v1 Eviction resource, used by the
    EvictionAccessor to POST eviction requests.
    """

    api_version: Literal["policy/v1"] = "policy/v1"
    kind: Literal["Eviction"] = "Eviction"
    metadata: ObjectMetadata | None = None
    delete_options: DeleteOptions | None = None
