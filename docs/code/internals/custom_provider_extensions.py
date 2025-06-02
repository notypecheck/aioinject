from collections.abc import Mapping
from typing import Any, TypeVar

from pydantic_settings import BaseSettings

from aioinject import Provider, Scope, SyncContainer
from aioinject.extensions import ProviderExtension
from aioinject.extensions.providers import (
    CacheDirective,
    ProviderInfo,
    ResolveDirective,
)


TSettings = TypeVar("TSettings", bound=BaseSettings)


class SettingsProvider(Provider[TSettings]):
    def __init__(self, settings_cls: type[TSettings]) -> None:
        self.implementation = settings_cls

    def provide(
        self,
        kwargs: dict[str, Any],  # noqa: ARG002
    ) -> TSettings:
        return self.implementation()


class SettingsProviderExtension(
    ProviderExtension[SettingsProvider[TSettings]],
):
    def supports_provider(self, provider: object) -> bool:
        return isinstance(provider, SettingsProvider)

    def extract(
        self,
        provider: SettingsProvider[TSettings],
        type_context: Mapping[str, type[object]],  # noqa: ARG002
    ) -> ProviderInfo[TSettings]:
        return ProviderInfo(
            interface=provider.implementation,
            type_=provider.implementation,
            dependencies=(),
            scope=Scope.lifetime,
            compilation_directives=(
                ResolveDirective(is_async=False, is_context_manager=False),
                CacheDirective(),
            ),
        )


class MySettings(BaseSettings):
    env_value: int


def main() -> None:
    container = SyncContainer(extensions=[SettingsProviderExtension()])
    container.register(SettingsProvider(MySettings))

    with container, container.context() as ctx:
        print(ctx.resolve(MySettings))  # env_value=...


if __name__ == "__main__":
    main()
