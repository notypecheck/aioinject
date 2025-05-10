import dataclasses
from typing import Generic

from aioinject._types import T
from aioinject.scope import BaseScope


@dataclasses.dataclass(slots=True, kw_only=True)
class Dependency(Generic[T]):
    name: str
    type_: type[T]


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


@dataclasses.dataclass(slots=True, kw_only=True)
class LockDirective(CompilationDirective):
    pass


@dataclasses.dataclass(kw_only=True)
class ProviderInfo(Generic[T]):
    interface: type[T]
    type_: type[T]
    dependencies: tuple[Dependency[object], ...]
    scope: BaseScope
    compilation_directives: tuple[CompilationDirective, ...]
