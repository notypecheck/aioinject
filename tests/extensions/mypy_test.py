from typing import Any

import aioinject
from aioinject import Context
from aioinject.context import ProviderRecord
from aioinject.extensions import OnResolveExtension


class _TestExtension(OnResolveExtension):
    async def on_resolve(
        self,
        context: Context,
        provider: ProviderRecord[Any],
        instance: Any,
    ) -> None: ...


async def _pass() -> None:
    aioinject.Container(extensions=[_TestExtension()])
