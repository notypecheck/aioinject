import abc
from collections.abc import Callable

from django.http import HttpRequest, HttpResponse

from aioinject import SyncContainer
from aioinject._types import P, T
from aioinject.decorators import base_inject


def inject(function: Callable[P, T]) -> Callable[P, T]:
    return base_inject(
        function,
        context_parameters=(),
        context_getter=lambda args, kwargs: args[0].__aioinject_context__,  # noqa: ARG005
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
