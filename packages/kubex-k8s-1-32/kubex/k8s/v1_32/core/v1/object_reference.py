from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class ObjectReference(BaseK8sModel):
    """ObjectReference contains enough information to let you inspect or modify the referred object."""

    api_version: str | None = Field(
        default=None, alias="apiVersion", description="API version of the referent."
    )
    field_path: str | None = Field(
        default=None,
        alias="fieldPath",
        description='If referring to a piece of an object instead of an entire object, this string should contain a valid JSON/Go field access statement, such as desiredState.manifest.containers[2]. For example, if the object reference is to a container within a pod, this would take on a value like: "spec.containers{name}" (where "name" refers to the name of the container that triggered the event) or if no container name is specified "spec.containers[2]" (container with index 2 in this pod). This syntax is chosen only to have some well-defined way of referencing a part of an object.',
    )
    kind: str | None = Field(
        default=None,
        alias="kind",
        description="Kind of the referent. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds",
    )
    name: str | None = Field(
        default=None,
        alias="name",
        description="Name of the referent. More info: https://kubernetes.io/docs/concepts/overview/working-with-objects/names/#names",
    )
    namespace: str | None = Field(
        default=None,
        alias="namespace",
        description="Namespace of the referent. More info: https://kubernetes.io/docs/concepts/overview/working-with-objects/namespaces/",
    )
    resource_version: str | None = Field(
        default=None,
        alias="resourceVersion",
        description="Specific resourceVersion to which this reference is made, if any. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#concurrency-control-and-consistency",
    )
    uid: str | None = Field(
        default=None,
        alias="uid",
        description="UID of the referent. More info: https://kubernetes.io/docs/concepts/overview/working-with-objects/names/#uids",
    )
