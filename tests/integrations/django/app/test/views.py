from django.http import HttpRequest, HttpResponse

from aioinject import Injected
from aioinject.ext.django import inject


@inject
def function_view(_: HttpRequest, number: Injected[int]) -> HttpResponse:
    return HttpResponse(content=f"Number {number}")


@inject
def function_view_with_parameter(
    _: HttpRequest, parameter: str, number: Injected[int]
) -> HttpResponse:
    return HttpResponse(content=f"Number {parameter} {number}")
