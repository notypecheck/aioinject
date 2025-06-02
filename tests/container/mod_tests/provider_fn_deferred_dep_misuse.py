from __future__ import annotations

from aioinject import Container, Singleton


cont = Container()


# notice that C is not defined yet
def get_c() -> C:
    return C()


cont.register(Singleton(get_c))


class C: ...
