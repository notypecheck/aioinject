from django.http import HttpRequest, HttpResponse

from aioinject import Injected
from aioinject.ext.django import inject


@inject
def root_view(
    _: HttpRequest,
    dependency: Injected[int],
) -> HttpResponse:
    return HttpResponse(content=f"{dependency}")
