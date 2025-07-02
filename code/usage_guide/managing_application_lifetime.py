import asyncio

from aioinject import Container


async def main() -> None:
    container = Container()

    async with container:
        ...


if __name__ == "__main__":
    asyncio.run(main())
