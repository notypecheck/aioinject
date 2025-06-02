import functools

from aioinject import SyncContainer
from aioinject.ext.django import SyncAioinjectMiddleware


@functools.cache
def create_container() -> SyncContainer:
    container = SyncContainer()
    # Register dependencies there
    return container


class DIMiddleware(SyncAioinjectMiddleware):
    container = create_container()
