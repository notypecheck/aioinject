from __future__ import annotations

from typing import Any, Protocol, TypeVar


_T = TypeVar("_T")


class Provider(Protocol[_T]):
    interface: type[_T] | None
    implementation: Any

    def provide(self, kwargs: dict[str, Any]) -> object: ...
