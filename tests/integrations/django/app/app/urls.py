from django.urls import path
from rest_framework.routers import DefaultRouter

from tests.integrations.django.app.drf.views import DRFView, DRFViewSet
from tests.integrations.django.app.test.views import (
    function_view,
    function_view_with_parameter,
)


router = DefaultRouter()
router.register(prefix="drf/viewset", viewset=DRFViewSet, basename="number")


urlpatterns = [
    path("dj/function", function_view),
    path("dj/function/<str:parameter>", function_view_with_parameter),
    path("drf/api-view", DRFView.as_view()),
    *router.urls,
]
