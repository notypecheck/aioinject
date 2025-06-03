from __future__ import annotations

import abc
from collections.abc import Callable
from typing import Any

from django.http import HttpRequest, HttpResponse

from aioinject import SyncContainer, SyncContext
from aioinject._types import P, T
from aioinject.decorators import base_inject


try:
    import rest_framework.request
except ImportError:  # pragma: no cover
    rest_framework = None  # type: ignore[assignment]


def context_getter(
    args: tuple[Any, ...], kwargs: dict[str, Any]
) -> SyncContext:
    request: HttpRequest | rest_framework.request.Request | None = next(
        (
            # Django/DRF always seem to pass request through args
            arg
            for arg in args
            if isinstance(
                arg,
                HttpRequest
                if rest_framework is None
                else (HttpRequest, rest_framework.request.Request),
            )
        ),
        None,
    )
    if request is None:  # pragma: no cover
        msg = (
            f"Could not find request parameter, expected one of the parameters to be 'django.http.HttpRequest' or 'rest_framework.request.Request':\n"
            f"  {args=}, {kwargs=}"
        )
        raise ValueError(msg)
    return request.__aioinject_context__  # type: ignore[attr-defined]


def inject(function: Callable[P, T]) -> Callable[P, T]:
    return base_inject(
        function,
        context_parameters=(),
        context_getter=context_getter,
    )


class SyncAioinjectMiddleware(abc.ABC):
    def __init__(
        self, get_response: Callable[[HttpRequest], HttpResponse]
    ) -> None:
        self.get_response = get_response

    @property
    @abc.abstractmethod
    def container(self) -> SyncContainer:
        raise NotImplementedError

    def __call__(self, request: HttpRequest) -> HttpResponse:
        with self.container.context() as ctx:
            request.__aioinject_context__ = ctx  # type: ignore[attr-defined]
            return self.get_response(request)
