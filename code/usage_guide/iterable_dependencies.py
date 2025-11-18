from collections.abc import Sequence

from aioinject import Singleton, SyncContainer


class Logger:
    pass


class FileLogger(Logger):
    pass


class DatabaseLogger(Logger):
    pass


class StreamLogger(Logger):
    pass


container = SyncContainer()
container.register(
    Singleton(FileLogger, Logger),
    Singleton(DatabaseLogger, Logger),
    Singleton(StreamLogger, Logger),
)

with container, container.context() as context:
    loggers = context.resolve(Sequence[Logger])  # type: ignore[type-abstract]
    print(loggers)  # [<FileLogger>, <DatabaseLogger>, <StreamLogger>]
