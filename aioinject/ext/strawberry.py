from __future__ import annotations

import inspect
import typing
from collections.abc import Callable, Iterator
from typing import Any

import strawberry
from strawberry.extensions import SchemaExtension


__all__ = ["AioInjectExtension", "inject"]

from strawberry.utils.typing import is_generic_alias

from aioinject import Container, Context, SyncContainer, SyncContext
from aioinject._types import P, T, safe_issubclass
from aioinject.decorators import ContextParameter, base_inject


def _find_strawberry_info_parameter(
    function: Callable[..., Any],
) -> inspect.Parameter | None:
    signature = inspect.signature(function)
    for p in signature.parameters.values():
        annotation = p.annotation

        if is_generic_alias(annotation):
            annotation = typing.get_origin(annotation)

        try:
            if safe_issubclass(annotation, strawberry.Info):
                return p
        except TypeError:  # pragma: no cover
            continue
    return None


def _default_context_getter(context: Any) -> Context | SyncContext:
    return context["aioinject_context"]


def _default_context_setter(
    context: Any, aioinject_context: Context | SyncContext
) -> None:
    context["aioinject_context"] = aioinject_context


def inject(
    function: Callable[P, T],
    context_getter: Callable[
        [Any], Context | SyncContext
    ] = _default_context_getter,
) -> Callable[P, T]:
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
        context_getter=lambda args, kwargs: context_getter(  # noqa: ARG005
            kwargs[info_parameter_name].context
        ),
        enter_context=True,
    )


class AioInjectExtension(SchemaExtension):
    def __init__(
        self,
        container: Container | SyncContainer,
        context_setter: Callable[
            [Any, Context | SyncContext], None
        ] = _default_context_setter,
    ) -> None:
        self.container = container
        self._context_setter = context_setter

    def on_operation(
        self,
    ) -> Iterator[None]:
        self._context_setter(
            self.execution_context.context, self.container.root
        )
        yield
