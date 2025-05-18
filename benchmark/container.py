from collections.abc import Sequence
from typing import Any

import aioinject
from aioinject import Provider
from benchmark.dependencies import (
    RepositoryA,
    RepositoryB,
    ServiceA,
    ServiceB,
    UseCase,
    create_session_cm,
)


providers: Sequence[Provider[Any]] = [
    aioinject.Scoped(create_session_cm),
    aioinject.Scoped(RepositoryA),
    aioinject.Scoped(RepositoryB),
    aioinject.Scoped(ServiceA),
    aioinject.Scoped(ServiceB),
    aioinject.Scoped(UseCase),
]


def create_container() -> aioinject.Container:
    container = aioinject.Container()
    container.register(*providers)
    return container
