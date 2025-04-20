from __future__ import annotations

import typing
from collections.abc import Sequence
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from aioinject._compilation.resolve import ProviderNode
    from aioinject.extensions.providers import Dependency


def create_var_name(dependency: ProviderNode) -> str:
    return dependency.name


def make_dependency_name(type_: type[object]) -> str:
    args = typing.get_args(type_)
    if not args:
        return type_.__name__
    args_str = "_".join(arg.__name__ for arg in args)
    return f"{type_.__name__}_{args_str}"


def generate_factory_kwargs(dependencies: Sequence[Dependency[object]]) -> str:
    kwargs = {
        dependency.name: f"{make_dependency_name(dependency.type_)}_instance"
        for dependency in dependencies
    }
    joined = ", ".join(f'"{k}": {v}' for k, v in kwargs.items())
    return "{" + joined + "}"
