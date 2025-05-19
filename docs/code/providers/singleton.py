import aioinject


container = aioinject.SyncContainer()
container.register(aioinject.Singleton(list))

with container.context() as ctx:
    object_1 = ctx.resolve(list)

with container.context() as ctx:
    object_2 = ctx.resolve(list)

assert object_1 is object_2
