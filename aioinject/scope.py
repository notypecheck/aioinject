from __future__ import annotations

import dataclasses
import enum
import functools


@dataclasses.dataclass(slots=True)
class ScopeValue:
    key: str


class BaseScope(enum.Enum):
    def __init__(self, value: ScopeValue) -> None:
        self.key = value.key


class Scope(BaseScope):
    lifetime = ScopeValue("lifetime")
    request = ScopeValue("request")


@functools.cache
def next_scope(scopes: type[BaseScope], scope: BaseScope | None) -> BaseScope:
    members = list(scopes.__members__.values())
    if scope is None:
        return members[0]

    index = members.index(scope)
    return members[index + 1]


class CurrentScope:
    """Special marker to indicate resolving FromContext dependency from current scope."""
