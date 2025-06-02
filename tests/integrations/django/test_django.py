import uuid
from http import HTTPStatus

from django.test import Client


def test_function_route(django_test_client: Client) -> None:
    response = django_test_client.get("/dj/function")
    assert response.status_code == HTTPStatus.OK
    assert response.content == b"Number 42"


def test_function_route_with_parameter(django_test_client: Client) -> None:
    parameter = str(uuid.uuid4())
    response = django_test_client.get(f"/dj/function/{parameter}")
    assert response.status_code == HTTPStatus.OK
    assert response.content == f"Number {parameter} 42".encode()
