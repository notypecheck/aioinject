import logging
from typing import TypeVar

from aioinject import Context
from aioinject.context import ProviderRecord
from aioinject.extensions import OnResolveExtension


T = TypeVar("T")


logger = logging.getLogger(__name__)


class MyExtension(OnResolveExtension):
    async def on_resolve(
        self,
        context: Context,  # noqa: ARG002
        provider: ProviderRecord[T],
        instance: T,  # noqa: ARG002
    ) -> None:
        logger.info("%s type was provided!", provider.info.type_)
