from __future__ import annotations

import inspect
import typing
from collections.abc import Callable, Iterator
from typing import Any

import strawberry
from strawberry.extensions import SchemaExtension


__all__ = ["AioInjectExtension", "inject"]

from strawberry.utils.typing import is_generic_alias

from aioinject import Container, SyncContainer
from aioinject._types import P, T
from aioinject.decorators import ContextParameter, base_inject


def _find_strawberry_info_parameter(
    function: Callable[..., Any],
) -> inspect.Parameter | None:
    signature = inspect.signature(function)
    for p in signature.parameters.values():
        annotation = p.annotation

        if is_generic_alias(annotation):
            annotation = typing.get_origin(annotation)

        if issubclass(annotation, strawberry.Info):
            return p
    return None


def inject(function: Callable[P, T]) -> Callable[P, T]:
    info_parameter = _find_strawberry_info_parameter(function)
    info_parameter_name = (
        info_parameter.name if info_parameter else "aioinject_info"
    )

    return base_inject(
        function=function,
        context_parameters=(
            ContextParameter(
                name=info_parameter_name,
                type_=strawberry.Info,
                remove=info_parameter is None,
            ),
        ),
        context_getter=lambda kwargs: kwargs[info_parameter_name].context[
            "aioinject_context"
        ],
        enter_context=True,
    )


class AioInjectExtension(SchemaExtension):
    def __init__(self, container: Container | SyncContainer) -> None:
        self.container = container

    def on_operation(
        self,
    ) -> Iterator[None]:
        self.execution_context.context["aioinject_context"] = (
            self.container.root
        )
        yield
