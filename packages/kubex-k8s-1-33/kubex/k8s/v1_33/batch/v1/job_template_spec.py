from pydantic import Field

from kubex.k8s.v1_33.batch.v1.job_spec import JobSpec
from kubex_core.models.base import BaseK8sModel
from kubex_core.models.metadata import ObjectMetadata


class JobTemplateSpec(BaseK8sModel):
    """JobTemplateSpec describes the data a Job should have when created from a template"""

    metadata: ObjectMetadata | None = Field(
        default=None,
        alias="metadata",
        description="Standard object's metadata of the jobs created from this template. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#metadata",
    )
    spec: JobSpec | None = Field(
        default=None,
        alias="spec",
        description="Specification of the desired behavior of the job. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#spec-and-status",
    )
