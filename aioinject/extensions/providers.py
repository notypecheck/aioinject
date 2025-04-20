import dataclasses
from functools import cached_property
from typing import Generic, TypeVar

from aioinject._types import is_iterable_generic_collection
from aioinject.scope import BaseScope


_T = TypeVar("_T")


@dataclasses.dataclass(slots=True, kw_only=True)
class Dependency(Generic[_T]):
    name: str
    type_: type[_T]

    def with_type(self, type_: type[_T]) -> "Dependency[_T]":
        return Dependency(name=self.name, type_=type_)

    def __hash__(self) -> int:
        return hash((self.name, self.type_))


@dataclasses.dataclass(slots=True, kw_only=True)
class CompilationDirective:
    is_enabled: bool = True


@dataclasses.dataclass(slots=True, kw_only=True)
class CacheDirective(CompilationDirective):
    optional: bool = True


@dataclasses.dataclass(slots=True, kw_only=True)
class ResolveDirective(CompilationDirective):
    is_async: bool
    is_context_manager: bool


@dataclasses.dataclass(kw_only=True)
class ProviderInfo(Generic[_T]):
    interface: type[_T]
    actual_type: type[_T]
    dependencies: tuple[Dependency[object], ...]
    scope: BaseScope
    compilation_directives: tuple[CompilationDirective, ...]

    @cached_property
    def is_iterable(self) -> bool:
        return is_iterable_generic_collection(self.interface)  # type: ignore[arg-type]
