from kubex import Api, create_api
from kubex.models.namespace import Namespace


async def main() -> None:
    api: Api[Namespace] = await create_api(Namespace)
    namespaces = await api.list()
    print(namespaces)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
