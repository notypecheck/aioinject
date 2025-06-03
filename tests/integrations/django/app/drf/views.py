from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ViewSet

from aioinject import Injected
from aioinject.ext.django import inject


class DRFView(APIView):
    @inject
    def get(self, _: Request, number: Injected[int]) -> Response:
        return Response({"value": number})


class DRFViewSet(ViewSet):
    @inject
    def retrieve(
        self,
        _: Request,
        pk: int,
        number: Injected[int],
    ) -> Response:
        return Response({"id": pk, "value": number})
