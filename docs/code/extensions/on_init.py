from datetime import datetime
from typing import NewType

from aioinject import Container, SyncContainer, Transient
from aioinject.extensions import OnInitExtension


Now = NewType("Now", datetime)


class TimeExtension(OnInitExtension):
    def on_init(
        self,
        container: Container | SyncContainer,
    ) -> None:
        container.register(Transient(datetime.now, Now))


container = SyncContainer(extensions=[TimeExtension()])
with container.context() as ctx:
    print(ctx.resolve(Now))
