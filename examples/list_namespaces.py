from kubex.api import Api
from kubex.client import create_client
from kubex.k8s.v1_35.core.v1.namespace import Namespace


async def main() -> None:
    client = await create_client()
    async with client:
        api: Api[Namespace] = Api(Namespace, client=client)
        namespaces = await api.list()
        print(namespaces)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
