from __future__ import annotations

import typing
from collections.abc import Sequence
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from aioinject._compilation.resolve import AnyNode, BoundDependency


def create_var_name(dependency: AnyNode) -> str:
    return dependency.name


def make_dependency_name(type_: type[object]) -> str:
    args = typing.get_args(type_)
    type_id = id(type_ if not args else typing.get_origin(type_))

    if not args:
        return f"{type_.__name__}_{type_id}"
    args_str = "_".join(arg.__name__ for arg in args)
    return f"{type_.__name__}_{args_str}_{type_id}"


def generate_factory_kwargs(
    dependencies: Sequence[BoundDependency[object]],
) -> str:
    kwargs = {
        dependency.name: f"{make_dependency_name(dependency.type_)}_instance"
        for dependency in dependencies
    }
    joined = ", ".join(f'"{k}": {v}' for k, v in kwargs.items())
    return "{" + joined + "}"
