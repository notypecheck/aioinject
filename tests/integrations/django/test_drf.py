import random
from http import HTTPStatus

from django.test import Client


def test_function_route(django_test_client: Client) -> None:
    response = django_test_client.get("/drf/api-view")
    assert response.status_code == HTTPStatus.OK
    assert response.json() == {"value": 42}


def test_api_view(django_test_client: Client) -> None:
    pk = random.randint(1, 1000)
    response = django_test_client.get(f"/drf/viewset/{pk}/")
    assert response.status_code == HTTPStatus.OK
    assert response.json() == {"value": 42, "id": str(pk)}
