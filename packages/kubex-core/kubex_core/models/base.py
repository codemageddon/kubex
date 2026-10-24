from __future__ import annotations

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class BaseK8sModel(BaseModel):
    """Base for every Kubernetes model.

    Fields are snake_case in Python and camelCase on the wire. Unknown fields
    (e.g. ones added by a newer API server than the model was generated for)
    are kept under their original wire keys and serialized back, so a
    get -> modify -> replace round-trip does not delete server data.
    """

    model_config = ConfigDict(
        alias_generator=to_camel, populate_by_name=True, extra="allow"
    )
