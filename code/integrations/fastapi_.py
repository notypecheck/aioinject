import contextlib
from collections.abc import AsyncIterator

import uvicorn
from fastapi import FastAPI

from aioinject import Container, Injected, Object
from aioinject.ext.fastapi import AioInjectMiddleware, FastAPIExtension, inject


container = Container(
    extensions=[FastAPIExtension()],  # (1)!
)
container.register(Object(42))


@contextlib.asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    async with container:  # (2)!
        yield


def create_app() -> FastAPI:
    app = FastAPI(lifespan=lifespan)
    app.add_middleware(AioInjectMiddleware, container=container)  # (3)!

    @app.get("/")
    @inject
    async def root(number: Injected[int]) -> int:
        return number

    return app


if __name__ == "__main__":
    uvicorn.run("main:create_app", factory=True, reload=True)
