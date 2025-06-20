from __future__ import annotations

import types
import typing
from collections.abc import Sequence
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from aioinject._compilation.resolve import AnyNode, BoundDependency


def create_var_name(node: AnyNode) -> str:
    return node.name


def make_dependency_name(type_: type[object]) -> str:
    args = typing.get_args(type_)
    type_id = id(type_ if not args else typing.get_origin(type_))
    if not args:
        return f"{type_.__name__}_{type_id}"

    args_str = "_".join(make_dependency_name(arg) for arg in args)
    if typing.get_origin(type_) == types.UnionType:
        return args_str

    return f"{type_.__name__}_{args_str}_{type_id}"


def generate_factory_kwargs(
    dependencies: Sequence[BoundDependency[object]],
) -> str:
    joined = ", ".join(
        f'"{dependency.name}": {dependency.variable_name}_instance'
        for dependency in dependencies
    )
    return "{" + joined + "}"
