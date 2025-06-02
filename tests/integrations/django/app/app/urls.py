from django.urls import path

from tests.integrations.django.app.test.views import (
    function_view,
    function_view_with_parameter,
)


urlpatterns = [
    path("dj/function", function_view),
    path("dj/function/<str:parameter>", function_view_with_parameter),
]
