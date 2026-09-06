from kubex_core.models.base import BaseK8sModel


class JSONSchemaPropsOrArray(BaseK8sModel):
    """JSONSchemaPropsOrArray represents a value that can either be a JSONSchemaProps or an array of JSONSchemaProps. Mainly here for serialization purposes."""
