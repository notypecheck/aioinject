from aioinject import Scoped, Singleton, SyncContainer


class Database:
    def __init__(self) -> None:
        self._storage = {1: "Username"}

    def get(self, id: int) -> str | None:
        return self._storage.get(id)


class UserService:
    def __init__(
        self,
        database: Database,  # <- `Database` is injected here
    ) -> None:
        self._database = database

    def get(self, id: int) -> str:
        user = self._database.get(id)
        if user is None:
            raise ValueError
        return user


container = SyncContainer()
container.register(
    Singleton(Database),
    Scoped(UserService),
)

with (
    container,  # Singletons are managed
    container.context() as context,
):
    service = context.resolve(UserService)
    user = service.get(1)
    print(user)  # "Username"
