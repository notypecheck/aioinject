import logging
from typing import TypeVar

from aioinject import InjectionContext, Provider
from aioinject.extensions import OnResolveExtension


T = TypeVar("T")


logger = logging.getLogger(__name__)


class MyExtension(OnResolveExtension):
    async def on_resolve(
        self,
        context: InjectionContext,  # noqa: ARG002
        provider: Provider[T],
        instance: T,  # noqa: ARG002
    ) -> None:
        logger.info("%s type was provided!", provider.type_)
