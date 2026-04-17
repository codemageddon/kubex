from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class SleepAction(BaseK8sModel):
    """SleepAction describes a "sleep" action."""

    seconds: int = Field(
        ..., alias="seconds", description="Seconds is the number of seconds to sleep."
    )
