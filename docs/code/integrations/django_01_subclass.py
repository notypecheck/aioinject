import functools
import random

from aioinject import Scoped, SyncContainer
from aioinject.ext.django import SyncAioinjectMiddleware


@functools.cache
def create_container() -> SyncContainer:
    container = SyncContainer()
    container.register(
        Scoped(lambda: random.randint(1, 1000), interface=int),  # noqa: S311
    )
    return container


class DIMiddleware(SyncAioinjectMiddleware):
    container = create_container()
