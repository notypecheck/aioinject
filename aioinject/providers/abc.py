from __future__ import annotations

from typing import Any, Protocol

from aioinject._types import FactoryResult, T_co


class Provider(Protocol[T_co]):
    implementation: Any

    def provide(self, kwargs: dict[str, Any]) -> FactoryResult[T_co]: ...
