from kubex_core.models.base import BaseK8sModel


class JSON(BaseK8sModel):
    """JSON represents any valid JSON value. These types are supported: bool, int64, float64, string, []interface{}, map[string]interface{} and nil."""
