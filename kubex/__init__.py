from pkgutil import extend_path

# Make `kubex` a mixed regular+namespace package so that `kubex.k8s.<version>`
# contributed by separately installed generator packages (kubex-k8s-1.30, ...)
# is importable alongside this package's own submodules.
__path__ = extend_path(__path__, __name__)

from .api import Api, create_api
from .client import BaseClient, create_client
from .configuration import ClientConfiguration

__all__ = ["Api", "BaseClient", "create_client", "ClientConfiguration", "create_api"]
