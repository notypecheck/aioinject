from typing import Generic, TypeVar


A = TypeVar("A")
B = TypeVar("B")


class AbstractService:
    pass


class AbstractImplA(AbstractService):
    pass


class AbstractImplB(AbstractService):
    pass


class Multi(Generic[A, B]):
    def __init__(self, a: A, b: B) -> None:
        self.a = a
        self.b = b
