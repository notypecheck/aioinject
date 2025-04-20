from __future__ import annotations

from typing import Any, Protocol

from aioinject._types import T


class Provider(Protocol[T]):
    interface: type[T] | None
    implementation: Any

    def provide(self, kwargs: dict[str, Any]) -> object: ...
