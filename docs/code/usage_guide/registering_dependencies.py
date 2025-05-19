from aioinject import Container, Scoped


class MyClass:
    pass


container = Container()
container.register(Scoped(MyClass))
