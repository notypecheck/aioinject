Internally when `Context.resolve` is called aioinject compiled whole dependency graph into a single function
and then uses it to resolve that specific type.

For example given a setup like this
```python
--8<-- "docs/code/internals/code_compilation_setup.py"
```

Generated factory function would look like this:

```python hl_lines="2-5 12-16 22 29-34"
async def factory(scopes: "Mapping[BaseScope, Context]") -> "T":
    lifetime_scope_cache = scopes[lifetime_scope].cache # (1)!
    lifetime_scope_exit_stack = scopes[lifetime_scope].exit_stack
    request_scope_cache = scopes[request_scope].cache
    request_scope_exit_stack = scopes[request_scope].exit_stack

    Service_now_a_Now_instance = Service_now_a_Now_provider.provide({})
    Service_now_b_Now_instance = Service_now_b_Now_provider.provide({})

    int_instance = int_provider.provide({})

    if ( # (2)!
        DBConnection_instance := request_scope_cache.get(
            DBConnection_type, NotInCache
        )
    ) is NotInCache:
        DBConnection_instance = (
            await request_scope_exit_stack.enter_async_context(
                DBConnection_provider.provide({})
            )
        )
        request_scope_cache[DBConnection_type] = DBConnection_instance # (3)!

    if (
        SingletonClient_instance := lifetime_scope_cache.get(
            SingletonClient_type, NotInCache
        )
    ) is NotInCache:
        async with scopes[lifetime_scope].lock: # (4)!
            if (
                SingletonClient_instance := lifetime_scope_cache.get(
                    SingletonClient_type, NotInCache
                )
            ) is NotInCache:
                SingletonClient_instance = SingletonClient_provider.provide({})
                lifetime_scope_cache[SingletonClient_type] = (
                    SingletonClient_instance
                )

    if (
        Service_instance := request_scope_cache.get(Service_type, NotInCache)
    ) is NotInCache:
        Service_instance = Service_provider.provide(
            {
                "now_a": Service_now_a_Now_instance,
                "now_b": Service_now_b_Now_instance,
                "int_object": int_instance,
                "connection": DBConnection_instance,
                "client": SingletonClient_instance,
            }
        )
        request_scope_cache[Service_type] = Service_instance

    return Service_instance

```

1. Used scope variables are set up
2. Relevant scope's cache is checked to see if dependency was already provided before
3. Provided instance is cached
4. Concurrent-sensitive providers are resolved under lock, also [double-checked locking](https://en.wikipedia.org/wiki/Double-checked_locking) is used

!!! note 
    Usually object id is appended to variable name (e.g. `DBConnection_140734497381936`) to avoid name conflicts, 
    here they're cleaned up.
