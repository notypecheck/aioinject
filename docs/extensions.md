Extensions are a mechanism to extend container and context behavior, similar to
a plugin system.

## Container Extensions

### Lifespan
Lifespan extension could be used to execute code when container enters and exits
```python
--8<-- "docs/code/extensions/lifespan.py"
```

### OnInit
OnInit extension is executed when container's `__init__` is called, this could
be used for example to register dependencies in it:
```python
--8<-- "docs/code/extensions/on_init.py"
```

### OnResolve / OnResolveSync
On resolve extension is called when individual dependency is provided within a context:
```python
--8<-- "docs/code/extensions/on_resolve.py"
```
