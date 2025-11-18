from typing import Final, Generic, TypeVar

from aioinject import Object, Scoped, SyncContainer


T = TypeVar("T")


class Box(Generic[T]):
    def __init__(self, value: T) -> None:
        self.value: Final = value

    def __repr__(self) -> str:
        return f"Box({self.value!r})"


container = SyncContainer()
container.register(
    Scoped(Box),
    Object("string value"),
    Object(42),
)

with container, container.context() as context:
    int_box = context.resolve(Box[int])
    print(int_box)  # Box(42)

    str_box = context.resolve(Box[str])
    print(str_box)  # Box('string value')

    container.register(Object(Box("bound"), interface=Box[str]))

    box_str = context.resolve(Box[str])
    print(box_str)  # Box('bound')
