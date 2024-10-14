from kubex.api.api import Api
from kubex.models.namespace import Namespace


async def main() -> None:
    api: Api[Namespace] = Api.all(Namespace)
    namespaces = await api.list()
    print(namespaces)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
