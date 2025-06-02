import functools

from aioinject import Scoped, SyncContainer
from aioinject.ext.django import SyncAioinjectMiddleware


@functools.cache
def create_container() -> SyncContainer:
    container = SyncContainer()
    container.register(
        Scoped(lambda: 42, interface=int),
    )

    return container


class DIMiddleware(SyncAioinjectMiddleware):
    container = create_container()
