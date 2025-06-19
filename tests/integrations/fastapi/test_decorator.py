from aioinject.ext.fastapi import inject


def test_decorator() -> None:
    @inject
    async def endpoint(param: list[str]) -> None:
        pass
