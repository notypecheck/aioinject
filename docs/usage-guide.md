## Registering Dependencies
To register a dependency pass provider you want into `Container.register`:
```python
--8<-- "docs/code/usage_guide/registering_dependencies.py"
```
You can pass multiple providers into the same call if needed:
```python
container.register(
    Scoped(A),
    Scoped(B),
)
```

## Generic Dependencies
Aioinject supports registering *unbound* generic classes and passing generic parameters when resolving them.
```python
--8<-- "docs/code/usage_guide/generics_unbound.py"
```
You can register bound generic type and it would take priority:
```python
container.register(Object(Box("bound"), interface=Box[str]))

with container.context() as context:
    box_str = context.resolve(Box[str]) 
    print(box_str)  # Box('bound')
```

## Iterable dependencies
Sometimes there's a need to register and resolve multiple dependencies of the same type/interface.  
Iterable dependencies in aioinject work similarly to `Enumerable` dependencies in `C#`/`.NET` - all dependencies
are instantiated and provided.

```python
--8<-- "docs/code/usage_guide/iterable_dependencies.py"
```
!!! warning
    When multiple providers are registered with same interface the most recent one would be provided:
    ```python
    context.resolve(Logger)  # <StreamLogger>
    ```
!!! note
    Currently iterable dependencies are always provided in a `list` container. 


## Context Managers / Resources
Applications often need to close dependencies after they're done using them,
this can be done by registering a function decorated with [`@contextlib.contextmanager`](https://docs.python.org/3/library/contextlib.html#contextlib.contextmanager)
or [`@contextlib.asynccontextmanager`](https://docs.python.org/3/library/contextlib.html#contextlib.asynccontextmanager).  
Internally aioinject would use [`contextlib.ExitStack`](https://docs.python.org/3/library/contextlib.html#contextlib.ExitStack) or [`contextlib.AsyncExitStack`](https://docs.python.org/3/library/contextlib.html#contextlib.AsyncExitStack) to manage them.

```python
--8<-- "docs/code/usage_guide/context_managers.py"
```

### Handling Errors
If Exceptions are raised inside a scope they're propagated into context managers, if you're not wrapping an
already existing context manager (e.g. SQLAlchemy's `Session.begin`) you should use `try-except-finally` to correctly close your dependencies.
```python
@contextlib.contextmanager
def dependency() -> Iterator[int]:
    obj = SomeObject()
    try:
        yield obj
    except:
        ... # Error handling code
    finally:
        obj.close()
```


## Managing Application Lifetime
In order for container to close singleton dependencies on application shutdown
you need to use container as a context manager.
```python
--8<-- "docs/code/usage_guide/managing_application_lifetime.py"
```
This also runs `LifespanExtension` and `LifespanSyncExtension`
