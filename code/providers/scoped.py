import aioinject


container = aioinject.SyncContainer()
container.register(aioinject.Scoped(list))

with container, container.context() as ctx:
    object_1 = ctx.resolve(list)
    object_2 = ctx.resolve(list)
    assert object_1 is object_2
